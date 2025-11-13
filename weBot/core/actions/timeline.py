"""Timeline interaction helpers (scrolling, post actions, etc.)."""
from __future__ import annotations

from typing import List, Optional

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..state import ActionResult, PageState, SessionContext
from .utils import human_type, micro_wait, random_delay, wait_for

ARTICLE_SELECTOR = "article[data-testid='tweet']"
COMPOSE_BUTTON_SELECTORS = (
    (By.CSS_SELECTOR, "a[data-testid='SideNav_NewTweet_Button']"),
    (By.CSS_SELECTOR, "button[data-testid='SideNav_NewTweet_Button']"),
    (By.CSS_SELECTOR, "a[aria-label='Post']"),
    (By.CSS_SELECTOR, "a[aria-label='Compose post']"),
    (By.CSS_SELECTOR, "button[aria-label='Post']"),
)
COMPOSE_TEXTAREA_SELECTOR = "div[data-testid='tweetTextarea_0']"
COMPOSE_SUBMIT_SELECTORS = (
    (By.CSS_SELECTOR, "button[data-testid='tweetButton']"),
    (By.CSS_SELECTOR, "button[data-testid='tweetButtonInline']"),
)


def update_post_cache(driver: WebDriver, context: SessionContext, timeout: float = 10) -> List[object]:
    posts = WebDriverWait(driver, timeout).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, ARTICLE_SELECTOR))
    )
    context.attributes["post_count"] = str(len(posts))
    return posts


def get_centered_post(driver: WebDriver) -> Optional[object]:
    return driver.execute_script(
        """
        var posts = document.querySelectorAll("article[data-testid='tweet']");
        var windowHeight = window.innerHeight;
        var centerY = windowHeight / 2;
        var closest = null;
        var closestDistance = Infinity;
        for (var i = 0; i < posts.length; i++) {
            var rect = posts[i].getBoundingClientRect();
            var distance = Math.abs(rect.top + rect.height / 2 - centerY);
            if (distance < closestDistance) {
                closest = posts[i];
                closestDistance = distance;
            }
        }
        return closest;
        """
    )


def refresh_feed(driver: WebDriver, context: SessionContext) -> List[object]:
    try:
        posts = update_post_cache(driver, context)
    except TimeoutException:
        context.attributes["post_count"] = "0"
        context.post_index = 0
        return []

    count = len(posts)
    if count == 0:
        context.post_index = 0
    else:
        context.post_index = min(context.post_index, count)
    return posts


def _find_next_post(driver: WebDriver, current_post: Optional[object]) -> Optional[object]:
    if current_post is None:
        posts = driver.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR)
        return posts[0] if posts else None
    try:
        return driver.execute_script(
            """
            const current = arguments[0];
            const posts = Array.from(document.querySelectorAll("article[data-testid='tweet']"));
            if (!posts.length) {
                return null;
            }
            const index = posts.indexOf(current);
            if (index === -1) {
                return posts[0];
            }
            if (index + 1 < posts.length) {
                return posts[index + 1];
            }
            return null;
            """,
            current_post,
        )
    except Exception:
        return None


def scroll(driver: WebDriver, context: SessionContext) -> ActionResult:
    try:
        current = get_centered_post(driver)
        target = _find_next_post(driver, current)

        if target is None:
            last_height = driver.execute_script("return document.body.scrollHeight")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            random_delay(1.2, 2.0, label="scroll_fetch")
            refresh_feed(driver, context)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height > last_height:
                current = get_centered_post(driver)
                target = _find_next_post(driver, current)
            if target is None:
                posts = driver.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR)
                target = posts[-1] if posts else None
                if target is None:
                    return ActionResult(False, PageState.HOME_TIMELINE, message="No more posts")

        if current is not None and target is current:
            refresh_feed(driver, context)
            return ActionResult(False, PageState.HOME_TIMELINE, message="No further posts available")

        driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", target)
        random_delay(0.5, 1.4, label="scroll_settle")
        context.post_index += 1
        refresh_feed(driver, context)
        return ActionResult(True, PageState.HOME_TIMELINE, metadata={"post_index": str(context.post_index)})
    except TimeoutException:
        return ActionResult(False, PageState.HOME_TIMELINE, message="Timeout during scroll")
    except Exception as exc:
        return ActionResult(False, PageState.ERROR, message=str(exc))


def _click_button_on_centered_post(driver: WebDriver, data_testid: str, aria_label_pattern: Optional[str] = None) -> bool:
    centered_post = get_centered_post(driver)
    if not centered_post:
        return False

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", centered_post)
    micro_wait()

    selector = f"button[data-testid='{data_testid}']"

    # Primary path: use JS within the same article element to avoid drifting to another post.
    try:
        js_button = driver.execute_script(
            """
            const post = arguments[0];
            const selector = arguments[1];
            const ariaPattern = arguments[2];
            if (!post) {
                return null;
            }
            const buttons = post.querySelectorAll(selector);
            if (!buttons.length) {
                return null;
            }
            if (!ariaPattern) {
                return buttons[0];
            }
            const lower = ariaPattern.toLowerCase();
            for (const button of buttons) {
                const label = (button.getAttribute('aria-label') || '').toLowerCase();
                if (label.includes(lower)) {
                    return button;
                }
            }
            return null;
            """,
            centered_post,
            selector,
            aria_label_pattern,
        )
    except Exception:
        js_button = None

    if js_button:
        driver.execute_script("arguments[0].click();", js_button)
        return True

    # Fallback: query inside the same centered post with Selenium APIs.
    try:
        scoped_selector = selector
        if aria_label_pattern:
            escaped = aria_label_pattern.replace('"', '\"')
            scoped_selector += f"[aria-label*=\"{escaped}\"]"
        button = centered_post.find_element(By.CSS_SELECTOR, scoped_selector)
        WebDriverWait(driver, 5).until(EC.element_to_be_clickable(button))
        driver.execute_script("arguments[0].click();", button)
        return True
    except (NoSuchElementException, TimeoutException, ElementClickInterceptedException, StaleElementReferenceException):
        return False


def like(driver: WebDriver) -> bool:
    return _click_button_on_centered_post(driver, "like", "Likes. Like")


def bookmark(driver: WebDriver) -> bool:
    return _click_button_on_centered_post(driver, "bookmark")


def repost(driver: WebDriver, *, quote: Optional[str] = None) -> bool:
    if not _click_button_on_centered_post(driver, "retweet", "Repost"):
        return False
    try:
        if quote:
            quote_button = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//a[@href='/compose/post']")), 5)
            driver.execute_script("arguments[0].click();", quote_button)
            random_delay(0.5, 1.0, label="pause_medium")
            quote_input = wait_for(driver, EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='textbox']")), 10)
            human_type(quote_input, quote)
            tweet_button = wait_for(driver, EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton']")), 10)
            driver.execute_script("arguments[0].click();", tweet_button)
            return True
        confirm = wait_for(driver, EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-testid='retweetConfirm']")), 5)
        driver.execute_script("arguments[0].click();", confirm)
        return True
    except TimeoutException:
        return False


def reply(driver: WebDriver, text: str) -> bool:
    if not _click_button_on_centered_post(driver, "reply", "Reply"):
        return False
    try:
        box = wait_for(driver, EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-testid='tweetTextarea_0']")), 10)
        human_type(box, text)
        button = wait_for(driver, EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='tweetButton']")), 10)
        driver.execute_script("arguments[0].click();", button)
        return True
    except TimeoutException:
        return False


def quote(driver: WebDriver, text: str) -> bool:
    return repost(driver, quote=text)


def comment(driver: WebDriver, text: str) -> bool:
    return reply(driver, text)


def describe_center_post(driver: WebDriver) -> Optional[str]:
    post = fetch_post(driver)
    if not post:
        return None
    username = post.get("username") or "Unknown user"
    text = (post.get("tweet_text") or "").strip()
    snippet = text[:140] + ("…" if len(text) > 140 else "")
    return f"{username}: {snippet}" if snippet else f"{username}: <no text>"


def go_to_top(driver: WebDriver) -> None:
    driver.execute_script("window.scrollTo(0, 0);")
    random_delay(0.3, 0.6, label="pause_short")


def create_post(driver: WebDriver, text: str) -> bool:
    try:
        compose_button = None
        for by, value in COMPOSE_BUTTON_SELECTORS:
            elements = driver.find_elements(by, value)
            if elements:
                compose_button = elements[0]
                break
        if compose_button is None:
            compose_button = wait_for(driver, EC.element_to_be_clickable(COMPOSE_BUTTON_SELECTORS[0]), 10)

        driver.execute_script("arguments[0].click();", compose_button)
        random_delay(0.3, 0.6, label="pause_short")

        textarea = wait_for(driver, EC.presence_of_element_located((By.CSS_SELECTOR, COMPOSE_TEXTAREA_SELECTOR)), 10)
        driver.execute_script("arguments[0].focus();", textarea)
        human_type(textarea, text)

        submit = None
        for by, value in COMPOSE_SUBMIT_SELECTORS:
            try:
                submit = wait_for(driver, EC.element_to_be_clickable((by, value)), 5)
                if submit:
                    break
            except TimeoutException:
                continue
        if submit is None:
            raise TimeoutException("Post submit button not found")

        driver.execute_script("arguments[0].click();", submit)
        random_delay(0.5, 1.0, label="pause_medium")
        return True
    except TimeoutException:
        return False


def open_author_profile(driver: WebDriver) -> bool:
    try:
        centered_post = get_centered_post(driver)
        if not centered_post:
            return False
        username_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article[data-testid='tweet'] div[data-testid='User-Name'] a"))
        )
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", username_element)
        micro_wait()
        driver.execute_script("arguments[0].click();", username_element)
        random_delay(0.8, 1.6, label="pause_long")
        return True
    except TimeoutException:
        return False


def follow(driver: WebDriver) -> bool:
    try:
        button = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//button[@data-testid][contains(@aria-label, 'Follow')]")), 10)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        micro_wait()
        driver.execute_script("arguments[0].click();", button)
        random_delay(0.5, 1.2, label="pause_medium_long")
        return True
    except TimeoutException:
        return False


def unfollow(driver: WebDriver) -> bool:
    # Simplified variant of the earlier unfollow logic
    try:
        unfollow_button = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//button[contains(@aria-label, 'Following') or contains(@aria-label, 'Unfollow')]")), 10)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", unfollow_button)
        micro_wait()
        driver.execute_script("arguments[0].click();", unfollow_button)
        random_delay(0.4, 1.0, label="menu_pause")
        confirm = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem' or @role='button']//span[contains(text(), 'Unfollow')]")), 5)
        driver.execute_script("arguments[0].click();", confirm)
        random_delay(0.4, 1.0, label="menu_pause")
        return True
    except TimeoutException:
        return False


def fetch_post(driver: WebDriver):
    centered = get_centered_post(driver)
    if not centered:
        return None
    try:
        username = driver.execute_script(
            "return arguments[0].querySelector(\"div[data-testid='User-Name'] span\").innerText;",
            centered,
        )
    except Exception:
        username = None
    try:
        tweet_text = driver.execute_script(
            "return arguments[0].querySelector(\"div[data-testid='tweetText']\")?.innerText || '';",
            centered,
        )
    except Exception:
        tweet_text = ""
    try:
        link = driver.execute_script(
            "var timeEl = arguments[0].querySelector('time'); return timeEl ? timeEl.parentElement.href : null;",
            centered,
        )
    except Exception:
        link = None
    # engagement stats reuse util.extract maybe later
    return {
        "username": username,
        "tweet_text": tweet_text,
        "link": link,
    }

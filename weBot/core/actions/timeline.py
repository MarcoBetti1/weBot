"""Timeline interaction helpers (scrolling, post actions, etc.)."""
from __future__ import annotations

from typing import Optional

from selenium.common.exceptions import ElementClickInterceptedException, NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from ..state import ActionResult, PageState, SessionContext
from .utils import human_type, micro_wait, random_delay, wait_for

ARTICLE_SELECTOR = "article[data-testid='tweet']"


def update_post_cache(driver: WebDriver, context: SessionContext, timeout: float = 10):
    context.attributes["post_count"] = str(
        len(
            WebDriverWait(driver, timeout).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ARTICLE_SELECTOR))
            )
        )
    )


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


def scroll(driver: WebDriver, context: SessionContext) -> ActionResult:
    try:
        posts = driver.find_elements(By.CSS_SELECTOR, ARTICLE_SELECTOR)
        if context.post_index < len(posts):
            target = posts[context.post_index]
            driver.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", target)
            random_delay(0.5, 1.4)
            context.post_index += 1
            return ActionResult(True, PageState.HOME_TIMELINE, metadata={"post_index": str(context.post_index)})
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_delay(1.2, 2.0)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height > last_height:
            context.post_index = max(0, context.post_index - 5)
            return ActionResult(True, PageState.HOME_TIMELINE)
        context.post_index = 0
        return ActionResult(False, PageState.HOME_TIMELINE, message="No more posts")
    except TimeoutException:
        return ActionResult(False, PageState.HOME_TIMELINE, message="Timeout during scroll")
    except Exception as exc:
        return ActionResult(False, PageState.ERROR, message=str(exc))


def _click_button_on_centered_post(driver: WebDriver, data_testid: str, aria_label_pattern: Optional[str] = None) -> bool:
    try:
        centered_post = get_centered_post(driver)
        if not centered_post:
            return False
        selector = f"button[data-testid='{data_testid}']"
        if aria_label_pattern:
            selector += f"[aria-label*='{aria_label_pattern}']"
        button = centered_post.querySelector(selector)
        if button:
            driver.execute_script("arguments[0].click();", button)
            return True
    except Exception:
        pass

    # fallback to selenium lookup when JS fails
    try:
        centered = get_centered_post(driver)
        if not centered:
            return False
        if aria_label_pattern:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f"article[data-testid='tweet'] button[data-testid='{data_testid}'][aria-label*='{aria_label_pattern}']",
                    )
                )
            )
        else:
            button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        f"article[data-testid='tweet'] button[data-testid='{data_testid}']",
                    )
                )
            )
        driver.execute_script("arguments[0].click();", button)
        return True
    except (TimeoutException, ElementClickInterceptedException, NoSuchElementException):
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
            random_delay(0.5, 1.0)
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
        random_delay(0.8, 1.6)
        return True
    except TimeoutException:
        return False


def follow(driver: WebDriver) -> bool:
    try:
        button = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//button[@data-testid][contains(@aria-label, 'Follow')]")), 10)
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        micro_wait()
        driver.execute_script("arguments[0].click();", button)
        random_delay(0.5, 1.2)
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
        random_delay(0.4, 1.0)
        confirm = wait_for(driver, EC.element_to_be_clickable((By.XPATH, "//div[@role='menuitem' or @role='button']//span[contains(text(), 'Unfollow')]")), 5)
        driver.execute_script("arguments[0].click();", confirm)
        random_delay(0.4, 1.0)
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

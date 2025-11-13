"""State recognition helpers that infer the current page from DOM cues."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from .state import PageState, StateSnapshot


@dataclass
class RecognizerConfig:
    home_aria_label: str = "Timeline: Your Home Timeline"
    followers_modal_selector: str = "div[aria-labelledby$='followers']"


def _element_exists(driver: WebDriver, by: By, value: str) -> bool:
    try:
        driver.find_element(by, value)
        return True
    except NoSuchElementException:
        return False


def recognize_state(driver: WebDriver, config: Optional[RecognizerConfig] = None) -> StateSnapshot:
    """Infer the current state using lightweight DOM heuristics."""
    config = config or RecognizerConfig()
    current_url = driver.current_url
    metadata: Dict[str, str] = {}

    # Login states
    if _element_exists(driver, By.NAME, "text") and "login" in current_url:
        metadata["step"] = "username"
        return StateSnapshot(PageState.LOGIN_USERNAME, current_url, metadata)
    if _element_exists(driver, By.XPATH, "//label[contains(., 'Phone or email')]"):
        metadata["step"] = "challenge-email"
        return StateSnapshot(PageState.LOGIN_CHALLENGE, current_url, metadata)
    if _element_exists(driver, By.NAME, "password"):
        metadata["step"] = "password"
        return StateSnapshot(PageState.LOGIN_PASSWORD, current_url, metadata)

    # Login error banner
    try:
        alerts = driver.find_elements(By.CSS_SELECTOR, "[role='alert']")
        for alert in alerts:
            text = (alert.text or "").strip()
            if text:
                metadata["message"] = text
                if "could not log" in text.lower() or "try again later" in text.lower():
                    return StateSnapshot(PageState.LOGIN_ERROR, current_url, metadata)
    except NoSuchElementException:
        pass

    # Followers modal
    if _element_exists(driver, By.CSS_SELECTOR, config.followers_modal_selector):
        return StateSnapshot(PageState.FOLLOWERS_MODAL, current_url, metadata)

    # Home timeline detection
    try:
        timeline = driver.find_element(By.CSS_SELECTOR, "div[data-testid='primaryColumn']")
        aria_label = (timeline.get_attribute("aria-label") or "").strip()
        if aria_label:
            metadata["aria_label"] = aria_label
            if config.home_aria_label.lower() in aria_label.lower() or "home timeline" in aria_label.lower():
                return StateSnapshot(PageState.HOME_TIMELINE, current_url, metadata)
        # Some builds expose the home indicator via aria-labelledby instead
        aria_labelledby = (timeline.get_attribute("aria-labelledby") or "").lower()
        if "home" in aria_labelledby and "timeline" in aria_labelledby:
            metadata["aria_labelledby"] = aria_labelledby
            return StateSnapshot(PageState.HOME_TIMELINE, current_url, metadata)
    except NoSuchElementException:
        pass

    # URL / nav fallbacks for home detection
    if any(token in current_url for token in ("/home", "?home")):
        metadata["url_match"] = "home"
        return StateSnapshot(PageState.HOME_TIMELINE, current_url, metadata)
    try:
        home_link = driver.find_element(By.CSS_SELECTOR, "a[data-testid='AppTabBar_Home_Link'][aria-current='page']")
        if home_link.is_displayed():
            metadata["nav"] = "home-active"
            return StateSnapshot(PageState.HOME_TIMELINE, current_url, metadata)
    except NoSuchElementException:
        pass

    # Profile page detection
    if "/status/" not in current_url and _element_exists(driver, By.CSS_SELECTOR, "div[data-testid='UserName']"):
        return StateSnapshot(PageState.PROFILE, current_url, metadata)

    # Search page detection
    if "search?q=" in current_url:
        metadata["query"] = current_url.split("search?q=")[-1]
        return StateSnapshot(PageState.SEARCH_RESULTS, current_url, metadata)

    return StateSnapshot(PageState.UNKNOWN, current_url, metadata)

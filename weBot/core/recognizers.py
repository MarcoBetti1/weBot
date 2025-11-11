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

    # Followers modal
    if _element_exists(driver, By.CSS_SELECTOR, config.followers_modal_selector):
        return StateSnapshot(PageState.FOLLOWERS_MODAL, current_url, metadata)

    # Home timeline detection
    try:
        timeline = driver.find_element(By.CSS_SELECTOR, "div[data-testid='primaryColumn']")
        aria_label = timeline.get_attribute("aria-label") or ""
        if config.home_aria_label in aria_label:
            metadata["aria_label"] = aria_label
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

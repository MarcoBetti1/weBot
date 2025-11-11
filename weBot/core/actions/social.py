"""Profile and social graph actions."""
from __future__ import annotations

from typing import List, Optional, Tuple

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from ..state import ActionResult, PageState
from .utils import random_delay, wait_for


FOLLOWER_MODAL_SELECTOR = "div[data-testid='sheetDialog']"
USER_CELL_SELECTOR = "div[data-testid='cellInnerDiv']"
USER_BUTTON_SELECTOR = "button[data-testid='UserCell']"
HANDLE_LINK_SELECTOR = "a[href^='/']"


def open_profile(driver: WebDriver, handle: str) -> ActionResult:
    url = f"https://twitter.com/{handle}"
    driver.get(url)
    random_delay(0.8, 1.6)
    return ActionResult(True, PageState.PROFILE, metadata={"handle": handle})


def navigate_follow_list(
    driver: WebDriver,
    handle: str,
    list_type: str,
    *,
    wait_seconds: float = 1.0,
) -> ActionResult:
    driver.get(f"https://twitter.com/{handle}/{list_type}")
    random_delay(wait_seconds, wait_seconds + 0.8)
    return ActionResult(True, PageState.FOLLOWERS_MODAL, metadata={"handle": handle, "list_type": list_type})


def collect_handles_from_modal(
    driver: WebDriver,
    *,
    max_count: Optional[int] = None,
    scroll_pause: Tuple[float, float] = (0.9, 1.6),
) -> Tuple[List[str], bool]:
    wait_for(driver, EC.presence_of_element_located((By.CSS_SELECTOR, USER_CELL_SELECTOR)), timeout=10)
    seen_handles: List[str] = []
    unique = set()
    fully_explored = False

    while True:
        user_cells = driver.find_elements(By.CSS_SELECTOR, USER_CELL_SELECTOR)
        for cell in user_cells:
            try:
                cell.find_element(By.CSS_SELECTOR, USER_BUTTON_SELECTOR)
                link = cell.find_element(By.CSS_SELECTOR, HANDLE_LINK_SELECTOR)
                href = link.get_attribute("href")
                if not href:
                    continue
                handle = href.rstrip("/").split("/")[-1]
                if handle and handle not in unique:
                    unique.add(handle)
                    seen_handles.append(handle)
                    if max_count and len(seen_handles) >= max_count:
                        return seen_handles, True
            except NoSuchElementException:
                continue

        previous_count = len(unique)
        driver.execute_script("document.documentElement.scrollTop += 600;")
        random_delay(*scroll_pause)
        if len(unique) == previous_count:
            fully_explored = True
            break

    return seen_handles, fully_explored

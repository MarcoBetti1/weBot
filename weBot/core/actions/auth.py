"""Authentication-related Selenium actions."""
from __future__ import annotations

import time
from typing import Optional, Sequence

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

from ..state import ActionError, ActionResult, PageState
from .utils import human_type, wait_for


def enter_login_identifier(driver: WebDriver, identifier: str, *, timeout: float = 10) -> ActionResult:
    if not identifier:
        raise ActionError("Cannot submit an empty login identifier.", PageState.LOGIN_USERNAME)

    field = wait_for(driver, EC.element_to_be_clickable((By.NAME, "text")), timeout)
    human_type(field, identifier)
    field.send_keys(Keys.RETURN)
    return ActionResult(success=True, metadata={"identifier": identifier})


def enter_challenge_email(driver: WebDriver, email: str, *, timeout: float = 10) -> ActionResult:
    if not email:
        raise ActionError("Email challenge requested but no email was supplied.", PageState.LOGIN_CHALLENGE)

    field = wait_for(driver, EC.element_to_be_clickable((By.NAME, "text")), timeout)
    human_type(field, email)
    field.send_keys(Keys.RETURN)
    return ActionResult(success=True)


def enter_password(driver: WebDriver, password: str, *, timeout: float = 10) -> ActionResult:
    field = wait_for(driver, EC.presence_of_element_located((By.NAME, "password")), timeout)
    human_type(field, password)
    field.send_keys(Keys.RETURN)
    return ActionResult(success=True, next_state=PageState.LOGIN_SUBMITTING)


def checkpoint_state(state: PageState, allowed: tuple[PageState, ...]):
    if state not in allowed:
        raise ActionError(
            f"State {state.name} is not valid for this action (expected one of {[s.name for s in allowed]}).",
            allowed[0],
        )


def maybe_solve_challenge(driver: WebDriver, *, email: Optional[str], current_state: PageState) -> Optional[ActionResult]:
    if current_state != PageState.LOGIN_CHALLENGE:
        return None
    if not email:
        raise ActionError("Challenge step encountered but email not provided.", PageState.LOGIN_CHALLENGE)
    return enter_challenge_email(driver, email)


def _collect_button_diagnostics(driver: WebDriver, limit: int = 8) -> list[str]:
    labels: list[str] = []
    try:
        candidates = driver.find_elements(By.CSS_SELECTOR, "[role='button'], button")
    except Exception:
        return labels

    for element in candidates:
        if not element.is_displayed():
            continue
        label = element.get_attribute("aria-label") or element.text
        if label:
            labels.append(label.strip())
        if len(labels) >= limit:
            break
    return labels


def _trigger_oauth_button(
    driver: WebDriver,
    selectors: Sequence[tuple[str, str]],
    *,
    timeout: float = 10,
    poll_interval: float = 0.4,
) -> ActionResult:
    deadline = time.time() + timeout
    last_error: Optional[Exception] = None

    while time.time() < deadline:
        for by, value in selectors:
            try:
                elements = driver.find_elements(by, value)
            except Exception as exc:  # pragma: no cover - diagnostic capture
                last_error = exc
                continue

            for button in elements:
                if not button.is_displayed():
                    continue
                try:
                    driver.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', inline: 'center'});",
                        button,
                    )
                    try:
                        button.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", button)
                    return ActionResult(True)
                except Exception as exc:  # pragma: no cover - diagnostic capture
                    last_error = exc
        time.sleep(poll_interval)

    result = ActionResult(False, message="OAuth button not found")
    if last_error:
        result.metadata["last_error"] = repr(last_error)
    result.metadata["attempted_selectors"] = [f"{by}:{value}" for by, value in selectors]
    labels = _collect_button_diagnostics(driver)
    if labels:
        result.metadata["visible_buttons"] = labels
    return result


def trigger_google_sign_in(driver: WebDriver, *, timeout: float = 10) -> ActionResult:
    selectors = [
        (By.CSS_SELECTOR, "div[role='button'][data-testid='login_with_google']"),
        (By.CSS_SELECTOR, "button[data-testid='login_with_google']"),
    ]
    selectors.extend(
        (By.XPATH, pattern)
        for pattern in (
            "//button[contains(@data-testid, 'google')]",
            "//div[contains(@data-testid, 'google') and @role='button']",
            "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'google')]/ancestor::*[@role='button']",
            "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'google')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'google')]",
        )
    )
    result = _trigger_oauth_button(driver, selectors, timeout=timeout)
    if result.success:
        result.metadata["provider"] = "google"
    return result


def trigger_apple_sign_in(driver: WebDriver, *, timeout: float = 10) -> ActionResult:
    selectors = [
        (By.CSS_SELECTOR, "div[role='button'][data-testid='login_with_apple']"),
        (By.CSS_SELECTOR, "button[data-testid='login_with_apple']"),
    ]
    selectors.extend(
        (By.XPATH, pattern)
        for pattern in (
            "//button[contains(@data-testid, 'apple')]",
            "//div[contains(@data-testid, 'apple') and @role='button']",
            "//span[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apple')]/ancestor::*[@role='button']",
            "//button[contains(translate(@aria-label, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apple')]",
            "//button[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'apple')]",
        )
    )
    result = _trigger_oauth_button(driver, selectors, timeout=timeout)
    if result.success:
        result.metadata["provider"] = "apple"
    return result

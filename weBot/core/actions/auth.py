"""Authentication-related Selenium actions."""
from __future__ import annotations

from typing import Optional

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

"""Login workflow built on the state-driven engine."""
from __future__ import annotations

import time
from typing import Dict

from selenium.webdriver.remote.webdriver import WebDriver

from ..core.actions import auth, navigation
from ..core.recognizers import recognize_state
from ..core.state import ActionResult, PageState, SessionContext
from ..core.workflow_engine import WorkflowEngine


def _handle_login_identifier(driver: WebDriver, context: SessionContext) -> ActionResult:
    identifier = context.next_login_identifier()
    return auth.enter_login_identifier(driver, identifier)


def _handle_login_challenge(driver: WebDriver, context: SessionContext) -> ActionResult:
    return auth.enter_challenge_email(driver, context.email or "")


def _handle_login_password(driver: WebDriver, context: SessionContext) -> ActionResult:
    return auth.enter_password(driver, context.password)


def _handle_login_submitting(driver: WebDriver, context: SessionContext) -> ActionResult:
    # Poll until we either reach home or are redirected elsewhere.
    for _ in range(20):
        snapshot = recognize_state(driver)
        if snapshot.state == PageState.HOME_TIMELINE:
            context.reset_login_cycle()
            return ActionResult(True, PageState.HOME_TIMELINE, metadata=snapshot.metadata)
        if snapshot.state in {PageState.LOGIN_CHALLENGE, PageState.LOGIN_PASSWORD}:
            context.reset_login_cycle()
            return ActionResult(True, snapshot.state, metadata=snapshot.metadata)
        time.sleep(0.5)
    metadata = {}
    last_identifier = context.attributes.get("last_login_identifier")
    if last_identifier:
        metadata["last_identifier"] = last_identifier
    return ActionResult(False, PageState.UNKNOWN, message="Login submission timeout", metadata=metadata)


def _handle_unknown(driver: WebDriver, context: SessionContext) -> ActionResult:
    # Attempt to navigate back to login URL as a recovery step
    navigation.navigate_to(driver, context, context.login_url)
    return ActionResult(True, PageState.LOGIN_USERNAME)


def build_login_workflow(driver: WebDriver, context: SessionContext) -> WorkflowEngine:
    handlers: Dict[PageState, callable] = {
        PageState.LOGIN_USERNAME: _handle_login_identifier,
        PageState.LOGIN_CHALLENGE: _handle_login_challenge,
        PageState.LOGIN_PASSWORD: _handle_login_password,
        PageState.LOGIN_SUBMITTING: _handle_login_submitting,
        PageState.UNKNOWN: _handle_unknown,
    }
    return WorkflowEngine(handlers=handlers, context=context, driver=driver, max_steps=30)

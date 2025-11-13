"""Navigation helpers built around state detection."""
from __future__ import annotations

import time
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from ...config.behaviour import get_behaviour_settings
from ..recognizers import recognize_state
from ..state import ActionResult, PageState, SessionContext


def navigate_to(
    driver: WebDriver,
    context: SessionContext,
    url: str,
    *,
    wait_seconds: float | None = None,
) -> ActionResult:
    settings = get_behaviour_settings()
    pause = settings.navigation_wait if wait_seconds is None else wait_seconds
    driver.get(url)
    time.sleep(pause)
    snapshot = recognize_state(driver)
    context.update_state(snapshot.state, **snapshot.metadata)
    context.post_index = 0
    return ActionResult(success=True, next_state=snapshot.state, metadata=snapshot.metadata)


def ensure_state(driver: WebDriver, context: SessionContext, desired: PageState, fallback_url: Optional[str] = None) -> PageState:
    snapshot = recognize_state(driver)
    if snapshot.state == desired:
        context.update_state(snapshot.state, **snapshot.metadata)
        return snapshot.state
    if fallback_url:
        navigate_to(driver, context, fallback_url)
        snapshot = recognize_state(driver)
        context.update_state(snapshot.state, **snapshot.metadata)
        return snapshot.state
    context.update_state(snapshot.state, **snapshot.metadata)
    return snapshot.state

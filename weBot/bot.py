"""High-level bot controller orchestrating driver, workflows, and actions."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from selenium.webdriver.remote.webdriver import WebDriver

from .core.actions import navigation, timeline
from .core.actions.utils import random_delay
from .core.driver import DriverConfig, DriverManager
from .core.recognizers import recognize_state
from .core.state import ActionResult, PageState, SessionContext


class BotController:
    """Entry point for interacting with Twitter/X via Selenium."""

    def __init__(
        self,
        *,
        login_url: str = "https://twitter.com/login",
        home_url: str = "https://twitter.com/home",
        driver_config: Optional[DriverConfig] = None,
    ):
        self.context = SessionContext(login_url=login_url, home_url=home_url)
        self.driver_manager = DriverManager(driver_config)
        self._driver: Optional[WebDriver] = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    @property
    def driver(self) -> WebDriver:
        if self._driver is None:
            raise RuntimeError("Driver has not been created. Call start() before using the bot.")
        return self._driver

    @property
    def profile_path(self) -> Optional[Path]:
        return self.driver_manager.profile_path

    @property
    def profile_is_persistent(self) -> bool:
        return self.driver_manager.profile_is_persistent

    def start(self) -> None:
        self._driver = self.driver_manager.create()

    def stop(self) -> None:
        self.driver_manager.quit()
        self._driver = None

    # ------------------------------------------------------------------
    # Login workflow (manual only)
    # ------------------------------------------------------------------
    def manual_login(
        self,
        *,
        manual_timeout: float | None = 600.0,
        persist_profile: bool = True,
    ) -> PageState:
        if self._driver is None:
            raise RuntimeError("Driver not started")

        self.context.set_login_method("manual")

        # Attempt to reuse an existing session before prompting for manual login.
        navigation.navigate_to(self.driver, self.context, self.context.home_url)
        if self.context.current_state == PageState.HOME_TIMELINE:
            self.context.logged_in = True
            if persist_profile:
                self.persist_profile()
            print("Existing session detected; already on home timeline.")
            return PageState.HOME_TIMELINE

        navigation.navigate_to(self.driver, self.context, self.context.login_url)
        random_delay(0.3, 0.6)

        state = self._manual_login(manual_timeout=manual_timeout)
        if state == PageState.HOME_TIMELINE and persist_profile:
            self.persist_profile()
        return state

    def persist_profile(self) -> Optional[Path]:
        path = self.driver_manager.persist_profile()
        if path:
            print(f"Chrome profile available for reuse: {path}")
        return path

    def _manual_login(self, *, manual_timeout: float | None = 600.0, poll_interval: float = 2.0) -> PageState:
        if manual_timeout is not None and manual_timeout <= 0:
            manual_timeout = None

        deadline = None if manual_timeout is None else time.time() + manual_timeout
        print("Manual login mode: complete authentication in the opened browser window.")
        if manual_timeout is None:
            print("Waiting indefinitely for the home timeline...")
        else:
            print(f"Waiting up to {int(manual_timeout)} seconds for the home timeline...")

        last_state: Optional[PageState] = None
        while True:
            snapshot = recognize_state(self.driver)
            self.context.update_state(snapshot.state, **snapshot.metadata)
            if snapshot.state != last_state:
                print(f"Detected page state: {snapshot.state.name}")
                last_state = snapshot.state
            if snapshot.state == PageState.HOME_TIMELINE:
                self.context.logged_in = True
                print("Manual login successful; captured home timeline.")
                return snapshot.state
            if deadline is not None and time.time() >= deadline:
                raise RuntimeError("Manual login timed out before reaching the home timeline.")
            time.sleep(poll_interval)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def _require_persisted_profile(self) -> None:
        if not self.profile_is_persistent:
            raise RuntimeError(
                "A saved Chrome profile is required. Run manual_login() first and reuse the persisted profile."
            )

    def go_home(self) -> PageState:
        self._require_persisted_profile()
        result = navigation.navigate_to(self.driver, self.context, self.context.home_url)
        timeline.go_to_top(self.driver)
        state = result.next_state or self.context.current_state
        if state == PageState.HOME_TIMELINE:
            self.context.logged_in = True
        timeline.refresh_feed(self.driver, self.context)
        return state

    def navigate(self, url: str) -> ActionResult:
        self._require_persisted_profile()
        result = navigation.navigate_to(self.driver, self.context, url)
        if (result.next_state or self.context.current_state) == PageState.HOME_TIMELINE:
            self.context.logged_in = True
        return result

    def ensure_home(self) -> PageState:
        self._require_persisted_profile()
        state = navigation.ensure_state(self.driver, self.context, PageState.HOME_TIMELINE, self.context.home_url)
        if state == PageState.HOME_TIMELINE:
            self.context.logged_in = True
        return state

    # ------------------------------------------------------------------
    # Timeline helpers
    # ------------------------------------------------------------------
    def scroll_feed(self) -> ActionResult:
        self._require_persisted_profile()
        result = timeline.scroll(self.driver, self.context)
        timeline.refresh_feed(self.driver, self.context)
        return result

    def fetch_center_post(self):
        self._require_persisted_profile()
        return timeline.fetch_post(self.driver)

    def like_center_post(self) -> bool:
        self._require_persisted_profile()
        return timeline.like(self.driver)

    def bookmark_center_post(self) -> bool:
        self._require_persisted_profile()
        return timeline.bookmark(self.driver)

    def repost_center_post(self, quote: Optional[str] = None) -> bool:
        self._require_persisted_profile()
        return timeline.repost(self.driver, quote=quote)

    def reply_to_center_post(self, text: str) -> bool:
        self._require_persisted_profile()
        return timeline.reply(self.driver, text)
    
    def quote_center_post(self, text: str) -> bool:
        self._require_persisted_profile()
        return timeline.quote(self.driver, text)
    
    def comment_on_center_post(self, text: str) -> bool:
        self._require_persisted_profile()
        return timeline.comment(self.driver, text)

    def selected_post_summary(self) -> Optional[str]:
        self._require_persisted_profile()
        return timeline.describe_center_post(self.driver)

    def make_post(self, text: str) -> bool:
        self._require_persisted_profile()
        return timeline.create_post(self.driver, text)

    def open_center_author(self) -> bool:
        self._require_persisted_profile()
        return timeline.open_author_profile(self.driver)

    def follow_current_profile(self) -> bool:
        self._require_persisted_profile()
        return timeline.follow(self.driver)

    def unfollow_current_profile(self) -> bool:
        self._require_persisted_profile()
        return timeline.unfollow(self.driver)

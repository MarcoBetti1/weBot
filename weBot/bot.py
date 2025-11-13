"""High-level bot controller orchestrating driver, workflows, and actions."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Iterable, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from .core.actions import navigation, timeline
from .core.actions.auth import trigger_apple_sign_in, trigger_google_sign_in
from .core.actions.utils import random_delay
from .core.driver import DriverConfig, DriverManager
from .core.recognizers import recognize_state
from .core.state import ActionResult, PageState, SessionContext
from .core.workflow_engine import WorkflowEngine
from .workflows.login import build_login_workflow


class BotController:
    """Entry point for interacting with Twitter/X via Selenium."""

    def __init__(
        self,
        *,
        username: Optional[str] = None,
        password: str,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        login_url: str = "https://twitter.com/login",
        home_url: str = "https://twitter.com/home",
        identifier_priority: Optional[Iterable[str]] = None,
        driver_config: Optional[DriverConfig] = None,
        cookies_path: Optional[Path] = None,
    ):
        identifier_map = {
            "username": username,
            "email": email,
            "phone": phone,
        }
        identifiers: list[str] = []
        if identifier_priority:
            for key in identifier_priority:
                value = identifier_map.get(key.lower())
                if value and value not in identifiers:
                    identifiers.append(value)
        else:
            for key in ("username", "email", "phone"):
                value = identifier_map.get(key)
                if value and value not in identifiers:
                    identifiers.append(value)
        if not identifiers:
            raise ValueError("No login identifiers provided; supply at least one of username, email, or phone.")

        self.context = SessionContext(
            username=username,
            password=password,
            email=email,
            phone=phone,
            login_url=login_url,
            home_url=home_url,
            login_identifiers=identifiers,
        )
        self.context.set_login_method("auto")
        self.driver_manager = DriverManager(driver_config)
        self._driver: Optional[WebDriver] = None
        self.cookies_path = cookies_path or Path("cookies.json")

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

    def start(self) -> None:
        self._driver = self.driver_manager.create()

    def stop(self) -> None:
        self.driver_manager.quit()
        self._driver = None

    # ------------------------------------------------------------------
    # Cookie management
    # ------------------------------------------------------------------
    def load_cookies(self) -> bool:
        if self._driver is None:
            return False
        if not self.cookies_path.exists():
            print(f"No cookies file found at {self.cookies_path.resolve()}.")
            return False
        with self.cookies_path.open("r", encoding="utf-8") as fh:
            cookies = json.load(fh)
        restored = 0
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
                restored += 1
            except Exception as exc:  # pragma: no cover - network/driver dependent
                print(f"Failed to add cookie {cookie.get('name')}: {exc}")
        if restored:
            print(f"Restored {restored} cookies from {self.cookies_path.resolve()}.")
        else:
            print(f"No cookies were restored from {self.cookies_path.resolve()}.")
        return True

    def save_cookies(self) -> None:
        if self._driver is None:
            return
        cookies = self.driver.get_cookies()
        with self.cookies_path.open("w", encoding="utf-8") as fh:
            json.dump(cookies, fh, indent=2)

    # ------------------------------------------------------------------
    # Workflows
    # ------------------------------------------------------------------
    def login(
        self,
        *,
        prefer_cookies: bool = True,
        method: str = "auto",
        manual_timeout: float | None = 600.0,
        preserve_profile: bool = False,
    ) -> PageState:
        if self._driver is None:
            raise RuntimeError("Driver not started")

        method = (method or "auto").lower()
        self.context.set_login_method(method)
        self.context.reset_login_cycle()
        self.driver.get(self.context.login_url)
        random_delay(0.3, 0.6)

        if prefer_cookies and self.load_cookies():
            self.driver.get(self.context.home_url)
            snapshot = recognize_state(self.driver)
            if snapshot.state == PageState.HOME_TIMELINE:
                self.context.logged_in = True
                self.context.update_state(snapshot.state, **snapshot.metadata)
                return snapshot.state
            # fall back to credential login if cookies invalid
            self.driver.get(self.context.login_url)

        initial_snapshot = recognize_state(self.driver)
        self.context.update_state(initial_snapshot.state, **initial_snapshot.metadata)

        if method == "manual":
            state = self._manual_login(manual_timeout=manual_timeout)
            preserve_profile = True
        elif method in {"google", "apple"}:
            trigger = trigger_google_sign_in if method == "google" else trigger_apple_sign_in
            result = trigger(self.driver)
            if not result.success:
                self._print_oauth_failure(method, result)
                self.context.set_login_method("manual")
                state = self._manual_login(manual_timeout=manual_timeout)
                preserve_profile = True
            else:
                state = self._wait_for_home(timeout=180)
        else:
            workflow: WorkflowEngine = build_login_workflow(self.driver, self.context)
            state = workflow.run()

        if state == PageState.HOME_TIMELINE:
            self.context.reset_login_cycle()
            self.save_cookies()
            if preserve_profile:
                persisted = self.driver_manager.persist_profile()
                if persisted:
                    print(f"Preserved Chrome profile for reuse: {persisted}")
            print(f"Cookies saved to {self.cookies_path.resolve()}")
        return state

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

    def _print_oauth_failure(self, method: str, result: ActionResult) -> None:
        print(f"{method.title()} sign-in button was not found. Switching to manual login.")
        if result.message:
            print(f"Message: {result.message}")
        if result.metadata:
            visible = result.metadata.get("visible_buttons")
            if visible:
                print("Visible buttons detected: " + ", ".join(visible))
            attempted = result.metadata.get("attempted_selectors")
            if attempted:
                print("Selectors tried: " + ", ".join(attempted))
            last_error = result.metadata.get("last_error")
            if last_error:
                print(f"Last error: {last_error}")

    def _wait_for_home(self, *, timeout: float = 90, poll_interval: float = 1.5) -> PageState:
        deadline = time.time() + timeout
        last_state = self.context.current_state
        while time.time() < deadline:
            snapshot = recognize_state(self.driver)
            last_state = snapshot.state
            self.context.update_state(snapshot.state, **snapshot.metadata)
            if snapshot.state == PageState.HOME_TIMELINE:
                self.context.logged_in = True
                return snapshot.state
            time.sleep(poll_interval)
        return last_state

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def go_home(self) -> PageState:
        result = navigation.navigate_to(self.driver, self.context, self.context.home_url)
        return result.next_state or self.context.current_state

    def navigate(self, url: str) -> ActionResult:
        return navigation.navigate_to(self.driver, self.context, url)

    def ensure_home(self) -> PageState:
        return navigation.ensure_state(self.driver, self.context, PageState.HOME_TIMELINE, self.context.home_url)

    # ------------------------------------------------------------------
    # Timeline helpers
    # ------------------------------------------------------------------
    def scroll_feed(self) -> ActionResult:
        return timeline.scroll(self.driver, self.context)

    def fetch_center_post(self):
        return timeline.fetch_post(self.driver)

    def like_center_post(self) -> bool:
        return timeline.like(self.driver)

    def bookmark_center_post(self) -> bool:
        return timeline.bookmark(self.driver)

    def repost_center_post(self, quote: Optional[str] = None) -> bool:
        return timeline.repost(self.driver, quote=quote)

    def reply_to_center_post(self, text: str) -> bool:
        return timeline.reply(self.driver, text)

    def open_center_author(self) -> bool:
        return timeline.open_author_profile(self.driver)

    def follow_current_profile(self) -> bool:
        return timeline.follow(self.driver)

    def unfollow_current_profile(self) -> bool:
        return timeline.unfollow(self.driver)

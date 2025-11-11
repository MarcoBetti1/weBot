"""High-level bot controller orchestrating driver, workflows, and actions."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from .core.driver import DriverConfig, DriverManager
from .core.recognizers import recognize_state
from .core.state import ActionResult, PageState, SessionContext
from .core.actions import navigation, timeline
from .core.actions.utils import random_delay
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

    def start(self) -> None:
        self._driver = self.driver_manager.create()

    def stop(self) -> None:
        self.driver_manager.quit()
        self._driver = None

    # ------------------------------------------------------------------
    # Cookie management
    # ------------------------------------------------------------------
    def load_cookies(self) -> bool:
        if not self.cookies_path.exists() or self._driver is None:
            return False
        with self.cookies_path.open("r", encoding="utf-8") as fh:
            cookies = json.load(fh)
        for cookie in cookies:
            self.driver.add_cookie(cookie)
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
    def login(self, *, prefer_cookies: bool = True) -> PageState:
        if self._driver is None:
            raise RuntimeError("Driver not started")

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

        workflow: WorkflowEngine = build_login_workflow(self.driver, self.context)
        state = workflow.run()
        if state == PageState.HOME_TIMELINE:
            self.context.reset_login_cycle()
            self.save_cookies()
        return state

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

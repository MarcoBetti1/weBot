"""Browser session management utilities."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


@dataclass
class DriverConfig:
    """Runtime configuration for a Selenium Chrome session."""

    window_size: str = "1280,900"
    window_position: Optional[str] = None
    headless: bool = False
    extra_arguments: Iterable[str] = field(default_factory=tuple)


class DriverManager:
    """Factory responsible for creating and disposing Selenium drivers."""

    def __init__(self, config: Optional[DriverConfig] = None):
        self.config = config or DriverConfig()
        self._driver: Optional[webdriver.Chrome] = None

    @property
    def driver(self) -> webdriver.Chrome:
        if self._driver is None:
            raise RuntimeError("Driver has not been created yet. Call create() first.")
        return self._driver

    def create(self) -> webdriver.Chrome:
        if self._driver:
            return self._driver

        options = webdriver.ChromeOptions()
        if self.config.window_size:
            options.add_argument(f"--window-size={self.config.window_size}")
        if self.config.window_position:
            options.add_argument(f"--window-position={self.config.window_position}")
        if self.config.headless:
            options.add_argument("--headless=new")

        # Baseline stability flags for CI/dev usage
        for flag in (
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-notifications",
            "--disable-infobars",
            "--disable-popup-blocking",
        ):
            options.add_argument(flag)

        for arg in self.config.extra_arguments:
            options.add_argument(arg)

        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )
        return self._driver

    def quit(self) -> None:
        if self._driver:
            self._driver.quit()
            self._driver = None

"""Browser session management utilities."""
from __future__ import annotations

import re
import shutil
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable, Optional

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


_PROFILE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def validate_profile_name(name: str) -> str:
    """Validate and normalise a user-supplied profile name."""

    candidate = name.strip()
    if not candidate:
        raise ValueError("Chrome profile name cannot be empty")
    if not _PROFILE_NAME_PATTERN.fullmatch(candidate):
        raise ValueError(
            "Chrome profile name must be 1-64 characters of letters, digits, hyphen, or underscore"
        )
    return candidate


@dataclass
class DriverConfig:
    """Runtime configuration for a Selenium Chrome session."""

    window_size: str = "1280,900"
    window_position: Optional[str] = None
    headless: bool = False
    extra_arguments: Iterable[str] = field(default_factory=tuple)
    user_data_dir: Optional[Path] = None
    use_ephemeral_profile: bool = True
    bootstrap_profile: bool = False
    profile_root: Optional[Path] = None
    user_agent: Optional[str] = None
    stealth: bool = True


class DriverManager:
    """Factory responsible for creating and disposing Selenium drivers."""

    def __init__(self, config: Optional[DriverConfig] = None):
        self.config = config or DriverConfig()
        self._driver: Optional[webdriver.Chrome] = None
        self._profile_path: Optional[Path] = None
        self._cleanup_profile: bool = False

    @property
    def driver(self) -> webdriver.Chrome:
        if self._driver is None:
            raise RuntimeError("Driver has not been created yet. Call create() first.")
        return self._driver

    @property
    def profile_path(self) -> Optional[Path]:
        return self._profile_path

    @property
    def profile_is_persistent(self) -> bool:
        return self._profile_path is not None and not self._cleanup_profile

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

        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Baseline stability flags for CI/dev usage
        for flag in (
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--disable-gpu",
            "--disable-notifications",
            "--disable-infobars",
            "--disable-popup-blocking",
            "--disable-background-networking",
            "--disable-sync",
            "--disable-push-messaging",
            "--disable-gcm-checkin",
            "--disable-gcm-registration",
            "--log-level=3",
        ):
            options.add_argument(flag)

        profile_path, cleanup_profile = self._resolve_profile_path()
        self._profile_path = profile_path
        self._cleanup_profile = cleanup_profile

        if profile_path:
            options.add_argument(f"--user-data-dir={profile_path}")
            options.add_argument("--profile-directory=Default")

        if self.config.user_agent:
            options.add_argument(f"--user-agent={self.config.user_agent}")

        for arg in self.config.extra_arguments:
            options.add_argument(arg)

        self._driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

        if self.config.stealth:
            self._apply_stealth(self._driver)

        return self._driver

    def quit(self) -> None:
        if self._driver:
            self._driver.quit()
            self._driver = None
        if self._cleanup_profile and self._profile_path and self._profile_path.exists():
            shutil.rmtree(self._profile_path, ignore_errors=True)
        self._profile_path = None
        self._cleanup_profile = False

    def persist_profile(self, *, root: Optional[Path] = None, name: Optional[str] = None) -> Optional[Path]:
        """Convert an ephemeral profile into a reusable one.

        Parameters
        ----------
        root:
            Directory where the profile should be moved. Defaults to
            ``config.profile_root`` or ``.webot/profiles``.
        name:
            Optional friendly name. When provided the profile folder is renamed
            to ``<root>/<name>``.

        Returns
        -------
        pathlib.Path | None
            Path to the persisted profile, or ``None`` if no profile was
            available.
        """

        if not self._profile_path:
            return None

        root_dir = root or self.config.profile_root or Path(".webot/profiles")
        root_dir = Path(root_dir).expanduser().absolute()
        root_dir.mkdir(parents=True, exist_ok=True)

        source = Path(self._profile_path).expanduser().absolute()

        if name is not None:
            friendly = validate_profile_name(name)
            candidate = (root_dir / friendly).expanduser().absolute()
            candidate.parent.mkdir(parents=True, exist_ok=True)
            if source == candidate:
                self._cleanup_profile = False
                self._profile_path = candidate
                return candidate
            if candidate.exists():
                raise FileExistsError(f"Chrome profile already exists: {candidate}")

            shutil.move(str(source), str(candidate))
            self._profile_path = candidate
            self._cleanup_profile = False
            return candidate

        if not self._cleanup_profile:
            self._profile_path = source
            return self._profile_path

        candidate = (root_dir / source.name).expanduser().absolute()
        counter = 0
        while candidate.exists():
            counter += 1
            candidate = root_dir / f"{source.name}-{counter}"

        shutil.move(str(source), str(candidate))
        self._profile_path = candidate.expanduser().absolute()
        self._cleanup_profile = False
        return self._profile_path

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _resolve_profile_path(self) -> tuple[Optional[Path], bool]:
        """Determine which Chrome profile directory to use.

        Returns
        -------
        tuple[pathlib.Path | None, bool]
            Path to the profile (if any) and a flag indicating whether it
            should be cleaned up on shutdown.
        """

        if self.config.user_data_dir:
            absolute = Path(self.config.user_data_dir).expanduser().absolute()
            absolute.parent.mkdir(parents=True, exist_ok=True)
            absolute.mkdir(parents=True, exist_ok=True)
            return absolute, False

        if self.config.bootstrap_profile:
            root = self.config.profile_root or Path(".webot/profiles")
            root = Path(root).expanduser().absolute()
            root.mkdir(parents=True, exist_ok=True)
            created = Path(tempfile.mkdtemp(prefix=self._profile_prefix(), dir=root))
            return created, False

        if self.config.use_ephemeral_profile:
            return Path(tempfile.mkdtemp(prefix="webot-chrome-")), True

        return None, False

    @staticmethod
    def _profile_prefix() -> str:
        return f"profile-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"

    def _apply_stealth(self, driver: webdriver.Chrome) -> None:  # pragma: no cover - dependent on Chrome
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                        Object.defineProperty(window, 'chrome', {value: { runtime: {} }});
                        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});
                        Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                        const originalQuery = window.navigator.permissions.query;
                        window.navigator.permissions.query = (parameters) => (
                          parameters.name === 'notifications'
                            ? Promise.resolve({ state: Notification.permission })
                            : originalQuery(parameters)
                        );
                    """,
                },
            )
        except Exception:
            pass

        if self.config.user_agent:
            try:
                driver.execute_cdp_cmd(
                    "Network.setUserAgentOverride",
                    {"userAgent": self.config.user_agent},
                )
            except Exception:
                pass

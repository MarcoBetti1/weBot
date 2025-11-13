"""Shared state definitions for workflows and actions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional


class PageState(Enum):
    UNKNOWN = auto()
    LANDING = auto()
    LOGIN_USERNAME = auto()
    LOGIN_CHALLENGE = auto()
    LOGIN_PASSWORD = auto()
    LOGIN_SUBMITTING = auto()
    LOGIN_ERROR = auto()
    HOME_TIMELINE = auto()
    PROFILE = auto()
    FOLLOWERS_MODAL = auto()
    SEARCH_RESULTS = auto()
    ERROR = auto()


@dataclass
class SessionContext:
    """Aggregated runtime metadata shared across workflows."""

    username: Optional[str]
    password: str
    email: Optional[str] = None
    phone: Optional[str] = None
    login_url: str = "https://twitter.com/login"
    home_url: str = "https://twitter.com/home"
    logged_in: bool = False
    current_state: PageState = PageState.UNKNOWN
    attributes: Dict[str, str] = field(default_factory=dict)
    post_index: int = 0
    login_identifiers: List[str] = field(default_factory=list)
    login_attempt: int = 0
    login_method: str = "auto"
    login_cycle: int = 0

    def update_state(self, new_state: PageState, **attributes: str) -> None:
        self.current_state = new_state
        if attributes:
            self.attributes.update(attributes)

    def next_login_identifier(self) -> str:
        identifiers = self.login_identifiers or [value for value in (self.username, self.email, self.phone) if value]
        if not identifiers:
            raise RuntimeError("No login identifiers are available; provide a username, email, or phone number.")
        index = self.login_attempt % len(identifiers)
        identifier = identifiers[index]
        self.login_attempt += 1
        self.login_cycle = self.login_attempt // len(identifiers)
        self.attributes["last_login_identifier"] = identifier
        return identifier

    def reset_login_cycle(self) -> None:
        self.login_attempt = 0
        self.login_cycle = 0
        self.attributes.pop("last_login_identifier", None)

    def set_login_method(self, method: str) -> None:
        self.login_method = method
        self.attributes["login_method"] = method


@dataclass
class StateSnapshot:
    """Point-in-time data describing the active page."""

    state: PageState
    url: str
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class ActionResult:
    """Return value for actions/handlers executed by workflows."""

    success: bool
    next_state: Optional[PageState] = None
    message: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


class ActionError(RuntimeError):
    """Raised when an action cannot be executed due to an invalid state."""

    def __init__(self, message: str, desired_state: Optional[PageState] = None):
        super().__init__(message)
        self.desired_state = desired_state


class TransitionError(RuntimeError):
    """Raised when a workflow state transition fails."""

    def __init__(self, message: str, source: PageState, target: Optional[PageState] = None):
        super().__init__(message)
        self.source = source
        self.target = target

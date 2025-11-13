"""Shared state definitions for workflows and actions."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, Optional


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

    login_url: str = "https://twitter.com/login"
    home_url: str = "https://twitter.com/home"
    logged_in: bool = False
    current_state: PageState = PageState.UNKNOWN
    attributes: Dict[str, str] = field(default_factory=dict)
    post_index: int = 0
    login_method: str = "manual"

    def __post_init__(self) -> None:
        self.attributes.setdefault("login_method", self.login_method)

    def update_state(self, new_state: PageState, **attributes: str) -> None:
        self.current_state = new_state
        if attributes:
            self.attributes.update(attributes)

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

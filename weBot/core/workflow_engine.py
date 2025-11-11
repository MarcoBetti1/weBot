"""Generic workflow engine that runs state-driven handlers."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict

from selenium.webdriver.remote.webdriver import WebDriver

from .recognizers import recognize_state
from .state import ActionResult, PageState, SessionContext, TransitionError

StateHandler = Callable[[WebDriver, SessionContext], ActionResult]


@dataclass
class WorkflowEngine:
    handlers: Dict[PageState, StateHandler]
    context: SessionContext
    driver: WebDriver
    max_steps: int = 20

    def run(self) -> PageState:
        steps = 0
        while steps < self.max_steps:
            snapshot = recognize_state(self.driver)
            self.context.update_state(snapshot.state, **snapshot.metadata)
            handler = self.handlers.get(snapshot.state)
            if handler is None:
                raise TransitionError(
                    f"No handler registered for state {snapshot.state.name}.",
                    snapshot.state,
                )
            result = handler(self.driver, self.context)
            next_state = result.next_state or recognize_state(self.driver).state
            self.context.update_state(next_state, **(result.metadata or {}))
            if result.success and next_state == PageState.HOME_TIMELINE:
                self.context.logged_in = True
                return next_state
            if not result.success and result.message:
                raise TransitionError(result.message, snapshot.state, next_state)
            steps += 1
        raise TransitionError("Workflow exceeded maximum allowed steps", self.context.current_state)

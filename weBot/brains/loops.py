"""Background loop scripts for continuous timeline interactions."""
from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional

from ..core.actions import timeline
from ..core.state import ActionResult

if TYPE_CHECKING:  # pragma: no cover - type checking helper without runtime import
    from ..bot import BotController
else:  # Fallback for runtime when annotations are not evaluated
    BotController = Any  # type: ignore[invalid-name]

ScriptFunction = Callable[[Any, threading.Event, logging.Logger, Dict[str, object]], None]


PRESET_COMMENTS = (
    "Appreciate this insight!",
    "Interesting perspective, thanks!",
    "Thanks for sharing.",
    "Really enjoyed this post!",
)


@dataclass(frozen=True)
class ScriptDefinition:
    """Metadata for a registered loop script."""

    name: str
    func: ScriptFunction
    description: str
    default_options: Dict[str, object] = field(default_factory=dict)


def _log_post(logger: logging.Logger, cycle: int, index: int, post: dict) -> None:
    username = (post.get("username") or "Unknown user").strip()
    text = (post.get("tweet_text") or "").strip().replace("\n", " ")
    if len(text) > 280:
        text = text[:277] + "..."
    logger.info("cycle=%s post=%s author=%s text=%s", cycle, index, username, text or "<no text>")


def random_engage_loop(
    bot: "BotController",
    stop_event: threading.Event,
    logger: logging.Logger,
    options: Dict[str, object],
) -> None:
    posts_per_cycle = int(options.get("posts_per_cycle", 10))
    iteration_limit = options.get("iteration_limit")
    if iteration_limit is not None:
        iteration_limit = int(iteration_limit)
    min_delay = float(options.get("min_delay", 0.8))
    max_delay = float(options.get("max_delay", 1.6))

    logger.info(
        "random_engage loop starting (posts_per_cycle=%s iteration_limit=%s)",
        posts_per_cycle,
        iteration_limit,
    )

    cycle = 0
    consecutive_errors = 0

    while not stop_event.is_set():
        cycle += 1
        try:
            bot.ensure_home()
            timeline.refresh_feed(bot.driver, bot.context)
        except Exception as exc:  # pragma: no cover - defensive logging
            consecutive_errors += 1
            logger.exception("failed to prepare home timeline: %s", exc)
            if consecutive_errors >= 3:
                logger.error("aborting random_engage loop after repeated setup failures")
                break
            time.sleep(2.0)
            continue

        consecutive_errors = 0
        processed = 0
        while processed < posts_per_cycle and not stop_event.is_set():
            processed += 1
            post = timeline.fetch_post(bot.driver)
            if post:
                _log_post(logger, cycle, processed, post)
                if random.random() < 0.30:
                    success = bot.like_center_post()
                    logger.info("cycle=%s post=%s like=%s", cycle, processed, success)
                if not stop_event.is_set() and random.random() < 0.20:
                    success = bot.repost_center_post()
                    logger.info("cycle=%s post=%s repost=%s", cycle, processed, success)
                if not stop_event.is_set() and random.random() < 0.10:
                    comment_text = random.choice(PRESET_COMMENTS)
                    success = bot.comment_on_center_post(comment_text)
                    logger.info(
                        "cycle=%s post=%s comment=%s text=%s",
                        cycle,
                        processed,
                        success,
                        comment_text,
                    )

            result: ActionResult = bot.scroll_feed()
            if not result.success:
                logger.warning(
                    "cycle=%s post=%s scroll failed: %s",
                    cycle,
                    processed,
                    result.message or "unknown error",
                )
                stop_event.wait(2.0)
                break

            # Allow cooperative cancellation between posts.
            if stop_event.wait(random.uniform(min_delay, max_delay)):
                break

        if iteration_limit is not None and cycle >= iteration_limit:
            logger.info("random_engage loop completed iteration_limit=%s", iteration_limit)
            break

        if stop_event.is_set():
            break

        try:
            bot.go_home()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("cycle=%s failed to reset home timeline: %s", cycle, exc)
            time.sleep(2.0)

        if stop_event.wait(random.uniform(2.0, 4.0)):
            break

    logger.info("random_engage loop stopped")


SCRIPT_REGISTRY: Dict[str, ScriptDefinition] = {
    "random_engage": ScriptDefinition(
        name="random_engage",
        func=random_engage_loop,
        description=(
            "Cycle through timeline posts with random like (30%), repost (20%), and comment (10%) actions. "
            "Processes 10 posts per cycle, returns home, and repeats until stopped."
        ),
        default_options={
            "posts_per_cycle": 10,
            "iteration_limit": None,
            "min_delay": 0.8,
            "max_delay": 1.6,
        },
    ),
}


class LoopManager:
    """Coordinate background execution of long-running scripts."""

    def __init__(self, bot: "BotController") -> None:
        self._bot = bot
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop_event: Optional[threading.Event] = None
        self._active_script: Optional[ScriptDefinition] = None

    # ------------------------------------------------------------------
    # Script registry accessors
    # ------------------------------------------------------------------
    def available_scripts(self) -> Dict[str, ScriptDefinition]:
        return dict(SCRIPT_REGISTRY)

    def is_running(self) -> bool:
        with self._lock:
            return bool(self._thread and self._thread.is_alive())

    def active_name(self) -> Optional[str]:
        with self._lock:
            return self._active_script.name if self._active_script else None

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------
    def start(
        self,
        name: str,
        *,
        logger: Optional[logging.Logger] = None,
        **overrides: object,
    ) -> None:
        definition = SCRIPT_REGISTRY.get(name)
        if definition is None:
            raise ValueError(f"Unknown script '{name}'. Use 'loop list' to view options.")

        with self._lock:
            if self._thread and self._thread.is_alive():
                raise RuntimeError("Another loop script is already running. Stop it before starting a new one.")

            options = dict(definition.default_options)
            options.update({k: v for k, v in overrides.items() if v is not None})

            try:
                min_delay = float(options["min_delay"])
                max_delay = float(options["max_delay"])
            except (KeyError, TypeError, ValueError):
                raise ValueError("Loop options must include numeric min_delay and max_delay values") from None
            if min_delay > max_delay:
                max_delay = min_delay
                options["max_delay"] = max_delay
            options["min_delay"] = min_delay
            options["max_delay"] = max_delay

            stop_event = threading.Event()
            log = logger or logging.getLogger(f"webot.loop.{definition.name}")

            def runner() -> None:
                try:
                    definition.func(self._bot, stop_event, log, options)
                except Exception:  # pragma: no cover - background safety
                    log.exception("Loop script '%s' terminated due to an unexpected error", definition.name)
                finally:
                    with self._lock:
                        self._thread = None
                        self._active_script = None
                        self._stop_event = None

            thread = threading.Thread(
                target=runner,
                name=f"weBot-loop-{definition.name}",
                daemon=True,
            )
            self._thread = thread
            self._stop_event = stop_event
            self._active_script = definition
            thread.start()

    def stop(self, *, wait: float | None = 5.0) -> bool:
        with self._lock:
            thread = self._thread
            event = self._stop_event
        if not thread or not event:
            return False

        event.set()
        if wait is not None:
            thread.join(timeout=wait)
        return True

    def status(self) -> Dict[str, object]:
        with self._lock:
            running = self._thread.is_alive() if self._thread else False
            script = self._active_script.name if self._active_script else None
        return {"running": running, "script": script}
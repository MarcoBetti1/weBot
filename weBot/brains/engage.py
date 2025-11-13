"""High-level routines for engaging with timeline content."""
from __future__ import annotations

import time
from typing import Optional

from ..config.behaviour import get_behaviour_settings
from ..core.state import ActionResult
from ..core.actions import timeline
from .policy import InteractionTracker, choose_actions, execute_actions


def process_feed(bot, *, posts: int = 10, tracker: Optional[InteractionTracker] = None) -> None:
    tracker = tracker or InteractionTracker()
    settings = get_behaviour_settings()

    for _ in range(posts):
        post = timeline.fetch_post(bot.driver)
        if post:
            actions = choose_actions(bot, post, tracker)
            execute_actions(bot, actions)
        result: ActionResult = timeline.scroll(bot.driver, bot.context)
        timeline.refresh_feed(bot.driver, bot.context)
        if not result.success:
            break
        time.sleep(settings.post_pause_seconds)

"""Interaction policy for deciding when to engage with a post."""
from __future__ import annotations

import random
from collections import deque
from dataclasses import dataclass
from typing import Iterable, List

from ..core.actions import timeline
from .scoring import calculate_post_score


@dataclass
class InteractionTracker:
    window_size: int = 100
    target_rate: float = 0.4

    def __post_init__(self):
        self.history = deque(maxlen=self.window_size)

    def add(self, interacted: bool) -> None:
        self.history.append(1 if interacted else 0)

    @property
    def rate(self) -> float:
        if not self.history:
            return 0.0
        return sum(self.history) / len(self.history)

    def should_interact(self) -> bool:
        current_rate = self.rate
        if current_rate < self.target_rate:
            return random.random() < 0.6
        if current_rate > self.target_rate:
            return random.random() < 0.2
        return random.random() < 0.4


def choose_actions(bot, post: dict, tracker: InteractionTracker) -> List[str]:
    score = calculate_post_score(post)
    if not tracker.should_interact() or score < 30:
        tracker.add(False)
        return []

    actions: List[str] = []
    if 30 <= score < 55:
        if random.random() < 0.3:
            actions.append("like")
    elif 55 <= score < 90:
        actions.extend(random.sample(["like", "bookmark", "reply"], k=random.choice([1, 2])))
    else:
        count = random.randint(2, 4)
        actions.extend(random.sample(["like", "bookmark", "reply", "repost"], k=count))

    tracker.add(bool(actions))
    return actions


def execute_actions(bot, actions: Iterable[str]) -> None:
    for name in actions:
        if name == "like":
            timeline.like(bot.driver)
        elif name == "bookmark":
            timeline.bookmark(bot.driver)
        elif name == "reply":
            timeline.reply(bot.driver, "Thanks for sharing this!")
        elif name == "repost":
            timeline.repost(bot.driver)

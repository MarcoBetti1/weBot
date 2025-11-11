"""Workflow for building follower graphs using BotController."""
from __future__ import annotations

import collections
from dataclasses import dataclass
from typing import Dict, Iterable, Set, Tuple

from ..bot import BotController
from ..core.actions import navigation, social
from ..core.state import PageState


@dataclass
class FollowerGraphResult:
    edges: Dict[str, Set[str]]
    visited: Set[str]


def collect_followers(bot: BotController, handle: str, *, max_count: int | None = None) -> Tuple[list[str], bool]:
    navigation.navigate_to(bot.driver, bot.context, f"https://twitter.com/{handle}/followers")
    followers, fully_explored = social.collect_handles_from_modal(bot.driver, max_count=max_count)
    return followers, fully_explored


def build_follower_graph(
    bot: BotController,
    start_handle: str,
    *,
    max_layers: int = 3,
    max_per_user: int = 40,
) -> FollowerGraphResult:
    graph: Dict[str, Set[str]] = {}
    visited: Set[str] = set()

    queue = collections.deque([(start_handle, 0)])

    while queue:
        current, depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        if depth >= max_layers:
            continue

        followers, _ = collect_followers(bot, current, max_count=max_per_user)
        for follower in followers:
            graph.setdefault(follower, set()).add(current)
            if follower not in visited:
                queue.append((follower, depth + 1))

    return FollowerGraphResult(edges=graph, visited=visited)

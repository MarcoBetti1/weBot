"""Workflow helpers for describing follower networks."""
from __future__ import annotations

import collections
import datetime
import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Literal, Optional, Set, Tuple

from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By

from ..bot import BotController
from ..core.actions import navigation, social


logger = logging.getLogger(__name__)

CollectionStatus = Literal[
    "collected",
    "no_followers",
    "private",
    "error",
    "skipped_depth_limit",
]


@dataclass
class FollowerCollectionDetails:
    """Low-level data extracted while inspecting a single handle."""

    handle: str
    followers: List[str]
    fully_explored: bool
    cutoff_reached: bool
    follower_count: Optional[int]
    follower_count_display: Optional[str]
    is_private: Optional[bool]
    has_followers: Optional[bool]
    status: CollectionStatus
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    url: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class AccountTraversalRecord:
    """Metadata captured for every handle enqueued during traversal."""

    handle: str
    depth: int
    status: CollectionStatus
    follower_count: Optional[int]
    follower_count_display: Optional[str]
    is_private: Optional[bool]
    has_followers: Optional[bool]
    indexed_count: int
    collection_limit: Optional[int]
    fully_explored: bool
    cutoff_reached: bool
    url: Optional[str]
    notes: List[str] = field(default_factory=list)
    error: Optional[str] = None
    metadata: Dict[str, str] = field(default_factory=dict)

    @property
    def truncated(self) -> bool:
        return self.cutoff_reached

    def to_dict(self) -> Dict[str, object]:
        return {
            "handle": self.handle,
            "depth": self.depth,
            "status": self.status,
            "follower_count": self.follower_count,
            "follower_count_display": self.follower_count_display,
            "is_private": self.is_private,
            "has_followers": self.has_followers,
            "followers_indexed": self.indexed_count,
            "collection_limit": self.collection_limit,
            "fully_explored": self.fully_explored,
            "cutoff_reached": self.cutoff_reached,
            "truncated": self.truncated,
            "url": self.url,
            "notes": self.notes,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class FollowerGraphResult:
    start_handle: str
    edges: Dict[str, Set[str]]
    visited: Set[str]
    nodes: Dict[str, AccountTraversalRecord]
    max_layers: int
    max_followers_per_user: Optional[int]
    generated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )

    def to_dict(self) -> Dict[str, object]:
        sorted_nodes = sorted(
            self.nodes.values(), key=lambda record: (record.depth, record.handle.lower())
        )
        node_payload = [record.to_dict() for record in sorted_nodes]
        edge_payload = [
            {"source": source, "target": target}
            for source in sorted(self.edges.keys())
            for target in sorted(self.edges[source])
        ]
        return {
            "start_handle": self.start_handle,
            "generated_at": self.generated_at.isoformat(),
            "settings": {
                "max_layers": self.max_layers,
                "max_followers_per_user": self.max_followers_per_user,
            },
            "summary": {
                "visited": len(self.visited),
                "edges": len(edge_payload),
                "truncated_nodes": [record.handle for record in sorted_nodes if record.truncated],
            },
            "nodes": node_payload,
            "edges": edge_payload,
        }


PrioritizeCallback = Callable[[str, FollowerCollectionDetails, int], Iterable[str]]
QueueEntry = Tuple[str, int]


def _parse_count(value: str | None) -> Optional[int]:
    if not value:
        return None
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    multiplier = 1
    suffix = cleaned[-1].lower()
    if suffix in {"k", "m", "b"} and cleaned[:-1]:
        cleaned = cleaned[:-1]
        multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}[suffix]
    try:
        return int(float(cleaned) * multiplier)
    except ValueError:
        return None


def _read_follower_count(driver) -> Tuple[Optional[int], Optional[str]]:
    selectors = (
        "a[href$='/followers'] > span > span",
        "a[href$='/followers'] span span",
    )
    for selector in selectors:
        try:
            text = driver.find_element(By.CSS_SELECTOR, selector).text.strip()
            if text:
                return _parse_count(text), text
        except NoSuchElementException:
            continue
    return None, None


def _detect_page_conditions(driver) -> Tuple[Optional[bool], Optional[bool], List[str]]:
    notes: List[str] = []
    is_private: Optional[bool] = None
    has_followers: Optional[bool] = None

    try:
        page_source = (driver.page_source or "").lower()
    except Exception:  # pragma: no cover - driver variability
        page_source = ""

    private_keywords = (
        "this account is protected",
        "these tweets are protected",
        "only approved followers",
        "private account",
    )
    if any(keyword in page_source for keyword in private_keywords):
        is_private = True
        notes.append("Protected/private account messaging detected.")

    empty_keywords = (
        "hasn't followed anyone yet",
        "doesn't have any followers",
        "does not have any followers",
        "no followers yet",
    )
    if any(keyword in page_source for keyword in empty_keywords):
        has_followers = False
        notes.append("Empty follower state text detected.")

    blocked_keywords = ("you're blocked", "you are blocked")
    if any(keyword in page_source for keyword in blocked_keywords):
        notes.append("Block notice detected while opening followers list.")

    suspended_keywords = (
        "account suspended",
        "has been suspended",
    )
    if any(keyword in page_source for keyword in suspended_keywords):
        notes.append("Suspension notice detected; results may be incomplete.")

    return is_private, has_followers, notes


def collect_followers(
    bot: BotController,
    handle: str,
    *,
    max_count: int | None = None,
) -> FollowerCollectionDetails:
    followers: List[str] = []
    fully_explored = False
    cutoff_reached = False
    follower_count: Optional[int] = None
    follower_count_display: Optional[str] = None
    is_private: Optional[bool] = None
    has_followers: Optional[bool] = None
    notes: List[str] = []
    metadata: Dict[str, str] = {"handle": handle}
    error: Optional[str] = None
    url: Optional[str] = None
    status: CollectionStatus = "collected"

    try:
        action_result = navigation.navigate_to(
            bot.driver,
            bot.context,
            f"https://twitter.com/{handle}/followers",
        )
        metadata.update(action_result.metadata or {})
        url = bot.driver.current_url
        follower_count, follower_count_display = _read_follower_count(bot.driver)
        is_private, has_followers, condition_notes = _detect_page_conditions(bot.driver)
        if condition_notes:
            notes.extend(condition_notes)
        if has_followers is None and follower_count == 0:
            has_followers = False
        followers, fully_explored = social.collect_handles_from_modal(
            bot.driver,
            max_count=max_count,
        )
        cutoff_reached = bool(followers and not fully_explored)
        if not followers:
            if is_private:
                status = "private"
            elif has_followers is False or follower_count == 0:
                status = "no_followers"
            else:
                notes.append(
                    "No followers returned; unable to confirm whether the list is empty or access was denied."
                )
        if cutoff_reached:
            notes.append("Follower list truncated before reaching the end of the modal.")
    except Exception as exc:  # pragma: no cover - Selenium variability
        logger.error("Failed to collect followers for '%s': %s", handle, exc)
        error = str(exc)
        status = "error"
        followers = []
        fully_explored = False
        cutoff_reached = False
        if not url:
            try:
                url = bot.driver.current_url
            except Exception:  # pragma: no cover - driver variability
                url = None
        notes.append("Exception encountered during follower collection.")

    if url:
        metadata.setdefault("url", url)

    return FollowerCollectionDetails(
        handle=handle,
        followers=followers,
        fully_explored=bool(fully_explored and status == "collected"),
        cutoff_reached=cutoff_reached if status == "collected" else False,
        follower_count=follower_count,
        follower_count_display=follower_count_display,
        is_private=is_private,
        has_followers=has_followers,
        status=status,
        notes=notes,
        error=error,
        url=url,
        metadata=metadata,
    )


def build_follower_graph(
    bot: BotController,
    start_handle: str,
    *,
    max_layers: int = 3,
    max_per_user: int = 40,
    prioritize_on_truncation: Optional[PrioritizeCallback] = None,
) -> FollowerGraphResult:
    graph: Dict[str, Set[str]] = {}
    visited: Set[str] = set()
    nodes: Dict[str, AccountTraversalRecord] = {}

    queue: collections.deque[QueueEntry] = collections.deque([(start_handle, 0)])

    while queue:
        current, depth = queue.popleft()
        if current in visited:
            continue
        visited.add(current)

        if depth >= max_layers:
            nodes[current] = AccountTraversalRecord(
                handle=current,
                depth=depth,
                status="skipped_depth_limit",
                follower_count=None,
                follower_count_display=None,
                is_private=None,
                has_followers=None,
                indexed_count=0,
                collection_limit=max_per_user,
                fully_explored=False,
                cutoff_reached=False,
                url=None,
                notes=["Traversal depth limit reached; followers not requested."],
            )
            continue

        collection = collect_followers(bot, current, max_count=max_per_user)
        record = AccountTraversalRecord(
            handle=current,
            depth=depth,
            status=collection.status,
            follower_count=collection.follower_count,
            follower_count_display=collection.follower_count_display,
            is_private=collection.is_private,
            has_followers=collection.has_followers,
            indexed_count=len(collection.followers),
            collection_limit=max_per_user,
            fully_explored=collection.fully_explored,
            cutoff_reached=collection.cutoff_reached,
            url=collection.url,
            notes=list(collection.notes),
            error=collection.error,
            metadata=dict(collection.metadata),
        )
        nodes[current] = record

        if collection.status != "collected":
            if collection.status == "private":
                logger.info(
                    "Handle '%s' appears to be private; skipping follower expansion.",
                    current,
                )
            elif collection.status == "no_followers":
                logger.info("Handle '%s' has no followers to index.", current)
            elif collection.status == "error":
                logger.error(
                    "Follower collection failed for '%s'; skipping expansion.",
                    current,
                )
            continue

        if record.cutoff_reached:
            logger.warning(
                "Follower list for '%s' truncated (collected %s handles; limit %s).",
                current,
                record.indexed_count,
                max_per_user,
            )

        for follower in collection.followers:
            graph.setdefault(follower, set()).add(current)
            if follower not in visited:
                queue.append((follower, depth + 1))

        if record.cutoff_reached and prioritize_on_truncation:
            try:
                prioritized = list(prioritize_on_truncation(current, collection, depth))
            except Exception as exc:  # pragma: no cover - callback variability
                logger.exception(
                    "prioritize_on_truncation callback failed for '%s': %s",
                    current,
                    exc,
                )
            else:
                for handle in reversed(prioritized):
                    if handle in visited:
                        continue
                    queue.appendleft((handle, depth + 1))

    return FollowerGraphResult(
        start_handle=start_handle,
        edges=graph,
        visited=visited,
        nodes=nodes,
        max_layers=max_layers,
        max_followers_per_user=max_per_user,
    )

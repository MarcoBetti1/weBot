"""Behaviour and timing configuration management."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple

try:  # Optional dependency for YAML support
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - YAML is optional
    yaml = None  # type: ignore


@dataclass(frozen=True)
class DelayRange:
    """Simple container for a minimum/maximum delay range."""

    minimum: float
    maximum: float

    def as_tuple(self) -> Tuple[float, float]:
        low = float(self.minimum)
        high = float(self.maximum)
        if high < low:
            low, high = high, low
        return low, high


@dataclass(frozen=True)
class BehaviourSettings:
    """Human-like timing controls used by the automation layers."""

    typing_delay: DelayRange = DelayRange(0.05, 0.2)
    random_delay: DelayRange = DelayRange(1.0, 3.0)
    micro_wait: DelayRange = DelayRange(0.05, 0.25)
    navigation_wait: float = 1.2
    post_pause_seconds: float = 0.5
    loop_error_pause: float = 2.0
    loop_cycle_pause: DelayRange = DelayRange(2.0, 4.0)
    named_ranges: Dict[str, DelayRange] = field(default_factory=dict)

    def resolve_range(self, label: str, fallback: Tuple[float, float]) -> Tuple[float, float]:
        entry = self.named_ranges.get(label)
        if entry:
            return entry.as_tuple()
        return fallback


DEFAULT_BEHAVIOUR = BehaviourSettings()
_CURRENT_SETTINGS: BehaviourSettings = DEFAULT_BEHAVIOUR


def get_behaviour_settings() -> BehaviourSettings:
    """Return the active behaviour configuration."""

    return _CURRENT_SETTINGS


def set_behaviour_settings(settings: BehaviourSettings) -> None:
    """Replace the active behaviour configuration."""

    global _CURRENT_SETTINGS
    _CURRENT_SETTINGS = settings


def load_behaviour_settings(path: Optional[Path] = None) -> BehaviourSettings:
    """Load behaviour settings from YAML or JSON.

    Parameters
    ----------
    path:
        Optional path to the configuration file. When omitted the loader looks
        for ``config/behavior.yaml`` or ``config/behaviour.yaml`` relative to the
        current working directory.
    """

    candidates: Iterable[Path]
    if path:
        candidates = (Path(path).expanduser(),)
    else:
        candidates = (
            Path("config/behavior.yaml"),
            Path("config/behaviour.yaml"),
        )

    last_error: Optional[Tuple[Path, Exception]] = None
    for candidate in candidates:
        file_path = candidate.expanduser().absolute()
        if not file_path.is_file():
            continue
        try:
            data = _read_config_file(file_path)
        except Exception as exc:  # pragma: no cover - pass through informative error
            last_error = (file_path, exc)
            continue
        return _parse_behaviour_settings(data)

    if last_error:
        failed_path, error = last_error
        raise RuntimeError(f"Failed to load behaviour configuration from {failed_path}: {error}") from error

    return DEFAULT_BEHAVIOUR


def _read_config_file(path: Path) -> Dict[str, object]:
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        if not yaml:
            raise RuntimeError("PyYAML is required to load YAML behaviour configuration files")
        loaded = yaml.safe_load(text) or {}
    else:
        loaded = json.loads(text)

    if not isinstance(loaded, dict):
        raise ValueError("Behaviour configuration must be a mapping at the top level")
    return loaded


def _parse_behaviour_settings(raw: Dict[str, object]) -> BehaviourSettings:
    def _range_from_mapping(obj: object, default: DelayRange) -> DelayRange:
        if not isinstance(obj, dict):
            return default
        minimum = obj.get("min") if isinstance(obj.get("min"), (int, float)) else default.minimum
        maximum = obj.get("max") if isinstance(obj.get("max"), (int, float)) else default.maximum
        return DelayRange(float(minimum), float(maximum))

    typing_delay = _range_from_mapping(raw.get("typing_delay"), DEFAULT_BEHAVIOUR.typing_delay)
    random_delay = _range_from_mapping(raw.get("random_delay"), DEFAULT_BEHAVIOUR.random_delay)
    micro_wait = _range_from_mapping(raw.get("micro_wait"), DEFAULT_BEHAVIOUR.micro_wait)

    navigation_wait = _coerce_number(raw.get("navigation_wait"), DEFAULT_BEHAVIOUR.navigation_wait)
    post_pause_seconds = _coerce_number(raw.get("post_pause_seconds"), DEFAULT_BEHAVIOUR.post_pause_seconds)

    loop_section = raw.get("loop") if isinstance(raw.get("loop"), dict) else {}
    loop_error_pause = _coerce_number(loop_section.get("error_pause"), DEFAULT_BEHAVIOUR.loop_error_pause)
    loop_cycle_pause = _range_from_mapping(loop_section.get("cycle_pause"), DEFAULT_BEHAVIOUR.loop_cycle_pause)

    named_ranges_raw = raw.get("named_ranges") if isinstance(raw.get("named_ranges"), dict) else {}
    named_ranges: Dict[str, DelayRange] = {}
    for key, value in named_ranges_raw.items():
        if not isinstance(key, str):
            continue
        if isinstance(value, dict):
            named_ranges[key] = _range_from_mapping(value, DEFAULT_BEHAVIOUR.random_delay)
        elif isinstance(value, (list, tuple)) and len(value) == 2:
            try:
                named_ranges[key] = DelayRange(float(value[0]), float(value[1]))
            except (TypeError, ValueError):
                continue

    return BehaviourSettings(
        typing_delay=typing_delay,
        random_delay=random_delay,
        micro_wait=micro_wait,
        navigation_wait=navigation_wait,
        post_pause_seconds=post_pause_seconds,
        loop_error_pause=loop_error_pause,
        loop_cycle_pause=loop_cycle_pause,
        named_ranges=named_ranges,
    )


def _coerce_number(value: object, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except (TypeError, ValueError):
        return default

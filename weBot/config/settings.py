"""Configuration helpers for runtime settings."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


@dataclass
class RuntimeSettings:
    """Optional environment-driven configuration."""

    profile_path: Optional[Path] = None


def load_runtime_settings(env_file: Optional[Path] = None) -> RuntimeSettings:
    """Load optional settings, including a persisted Chrome profile path.

    The function looks for ``WEBOT_PROFILE_PATH`` in the active environment and
    returns it (if present) as a ``pathlib.Path``. Supplying an ``env_file``
    mirrors the previous behaviour of loading variables from a ``.env`` file.
    """

    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    profile_value = os.getenv("WEBOT_PROFILE_PATH")
    profile_path = Path(profile_value).expanduser() if profile_value else None
    return RuntimeSettings(profile_path=profile_path)

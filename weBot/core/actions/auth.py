"""Deprecated automation helpers.

The project now supports manual login only. This module intentionally raises an
error so callers migrate to the new flow.
"""

from __future__ import annotations

raise ImportError(
    "weBot.core.actions.auth has been removed. Perform login manually and reuse the saved browser profile."
)

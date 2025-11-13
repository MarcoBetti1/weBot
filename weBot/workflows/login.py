"""Legacy login workflow placeholder.

Automated credential-based login has been removed. Use the manual login flow by
invoking ``BotController.manual_login`` and reusing the saved profile for future
workflows.
"""

from __future__ import annotations

raise ImportError(
    "weBot.workflows.login is no longer available. Manual login with a persisted browser profile is required."
)

"""Legacy ``scripts.secrets`` placeholder.

Use ``weBot.config.settings.load_credentials`` directly; this module no longer
exposes credential values.
"""

from __future__ import annotations


raise ImportError(
	"The 'scripts.secrets' module has been removed. Call"
	" weBot.config.settings.load_credentials() in your own code."
)
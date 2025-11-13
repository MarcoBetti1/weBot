# Loop Script System

The loop system enables long-running background routines that continuously interact with the timeline during an interactive session.

## Available Loop Commands

Use these commands from the interactive `session` shell:

- `loop list` — show all registered loop scripts with a short description.
- `loop status` — display whether a loop is currently active.
- `loop [start] SCRIPT_NAME [options]` — launch a loop script. If no action is provided, `start` is assumed.
- `loop stop` — request the active loop to stop gracefully.
- `stop` — shorthand for immediately issuing `loop stop` while keeping the interactive session open.

While a loop is running, other commands are blocked until the loop finishes or you stop it. This prevents race conditions with the browser state.

## random_engage Script

The first built-in script is `random_engage`, which cycles through the home timeline and performs lightweight engagement with each post.

Default behaviour per cycle:

1. Ensure the browser is on the home timeline and refresh the feed cache.
2. For the next 10 posts (configurable via `--posts-per-cycle`):
   - Log the author handle and text content (truncated to 280 characters) in the session log.
   - 30% chance to like, 20% chance to repost, 10% chance to leave a short comment selected from preset phrases.
   - Scroll to the next post with natural delays between actions.
3. Return to the top of the feed and repeat until stopped. If `--iterations` is provided, the loop stops after the specified number of cycles.

Optional CLI overrides when starting the loop:

- `--posts-per-cycle N` (default `10`)
- `--iterations N` — limits the number of cycles; omit for infinite loops.
- `--min-delay SECONDS` and `--max-delay SECONDS` — control randomized delays between posts.

## Logging

Loop scripts write structured entries to the interactive session log (e.g., `logs/session-YYYYMMDD-HHMMSS.log`). These logs capture post metadata and the result of each action, which is useful for auditing automated interactions.

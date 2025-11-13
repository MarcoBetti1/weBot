# `process_feed` (weBot/brains/engage.py)

- **Purpose:** High-level loop that evaluates posts on the home timeline and executes policy-driven actions.
- **Inputs:**
  - `bot`: an initialised and authenticated `BotController`.
  - `posts`: number of iterations to attempt.
  - `tracker`: optional `InteractionTracker` to preserve engagement history across runs.
- **Flow:**
  1. Fetches the centred post via `timeline.fetch_post`.
  2. Uses `choose_actions` to select a set of interactions based on scoring heuristics.
  3. Executes the actions (like/repost/comment/quote/etc.).
  4. Calls `timeline.scroll` to advance to the next post, then `timeline.refresh_feed` to resynchronise the DOM cache.
  5. Breaks early if scrolling fails or the timeline ends.
- **Delays:** Sleeps 0.5 seconds between iterations to emulate human pacing.
- **Errors:** Underlying Selenium exceptions surface via `timeline.scroll`/`timeline.refresh_feed` and stop the loop gracefully.

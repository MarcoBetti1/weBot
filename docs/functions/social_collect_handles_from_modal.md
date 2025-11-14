# `collect_handles_from_modal` (weBot/core/actions/social.py)

- **Signature:** `collect_handles_from_modal(driver, *, max_count=None, scroll_pause=(0.9, 1.6)) -> (list[str], bool)`
- **Purpose:** Scrolls the followers/following modal, extracting unique user handles.
- **Preconditions:** Assumes the caller already navigated to a URL that opens a modal populated with user cells.

## Algorithm
1. Waits up to 10 seconds for at least one follower "cell" to appear.
   - If the modal never populates, the function logs `INFO` and returns `([], True)` so upstream workflows can continue gracefully.
2. Iteratively:
   - Scans visible cells, collecting the trailing segment of each profile link (`/handle`).
   - Stops early once `max_count` handles have been collected (flagging `fully_explored=True`).
   - Executes a JavaScript scroll step (`document.documentElement.scrollTop += 600`) and waits for a human-like pause.
   - Detects completion when no new handles are found between iterations.
3. Returns the accumulated `seen_handles` and a boolean indicating whether the list was fully explored.

## Error Handling & Logging
- Catches Selenium `TimeoutException` thrown by the initial `wait_for` call and responds with an empty list.
- Wraps the scroll script in a `try/except`; if Chrome refuses the scroll (e.g., modal closed unexpectedly), it logs a warning and exits the loop.
- Uses the module logger (`logging.getLogger(__name__)`) so the session log captures collection anomalies.

## Usage Notes
- Designed to be invoked by workflows that gather follower or following lists after navigation to the modal.
- Returns unique handles while preserving discovery order so downstream code can replay interactions deterministically.

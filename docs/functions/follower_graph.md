# Follower Graph Workflow (weBot/workflows/follower_graph.py)

## `collect_followers(bot, handle, *, max_count=None) -> (list[str], bool)`
- **Role:** Navigate to the follower list for `handle` and proxy to `social.collect_handles_from_modal`.
- **Resilience:**
  - Wraps the entire collection in a `try/except` to prevent Selenium errors from halting the BFS.
  - Logs informative messages when no followers are returned or when collection fails.
- **Returns:**
  - `followers`: ordered list of unique handles (may be empty).
  - `fully_explored`: `False` if the modal could not be traversed completely (e.g., truncated by `max_count` or an error).

## `build_follower_graph(bot, start_handle, *, max_layers=3, max_per_user=40)`
- **Goal:** Breadth-first traversal to build a follower adjacency map starting from `start_handle`.
- **Data structures:**
  - `graph`: dict mapping follower handle -> set of accounts they follow (edges).  Suitable for exporting to CSV or NetworkX.
  - `visited`: set of handles already expanded to avoid cycles and repeated work.
- **Traversal Steps:**
  1. Initialise a queue with `(start_handle, depth=0)`.
  2. Pop entries breadth-first; skip already visited accounts and respect `max_layers`.
  3. Call `collect_followers` for each handle. If the returned list is empty, log and continue without enqueuing.
  4. When `collect_followers` reports `fully_explored=False`, log a warning indicating the list may be truncated.
  5. For each follower discovered, add an edge `follower -> current` and enqueue `(follower, depth+1)` if unseen.
- **Logging:** Uses the module logger to record:
  - Empty follower lists (informational).
  - Potentially truncated results (warning).
  - Exceptions raised by Selenium (error, with the exception message).
- **Outcome:** Returns `FollowerGraphResult` containing `edges` and `visited` for downstream reporting or analysis.

## Testing Tips
- Combine with the interactive session (`python -m main session`) to run successive `follower-graph` commands without reopening Chrome.
- Keep `max_per_user` small during manual testing to limit API calls and render cycles.
- Inspect the session log under `logs/` for detailed timing and error messages when traversals skip nodes.

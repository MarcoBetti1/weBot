# Follower Graph Workflow

The follower graph workflow performs a breadth-first crawl of follower relationships while capturing descriptive metadata about every account that is inspected. The workflow is designed to help spot coordinated networks and explain why certain profiles produce fewer edges (for example, private or empty accounts).

## Collection limits
- `max_per_user` controls how many followers are fetched for each account. It is exposed on the CLI as `--max-per-user` and inside `build_follower_graph` as the `max_per_user` keyword argument.
- When the modal is truncated because the limit is reached or scrolling stops early, the workflow records `cutoff_reached=True` for that node and logs a warning.
- Depth is constrained by `max_layers`. Accounts discovered at or beyond the limit are kept in the result set with the status `skipped_depth_limit` so downstream tooling understands why they were not fetched.

## Account statuses & metadata
Each visited handle receives an `AccountTraversalRecord` with:
- `status`: one of `collected`, `no_followers`, `private`, `error`, or `skipped_depth_limit`.
- `follower_count` and `follower_count_display`: quick insight into public follower numbers.
- `followers_indexed`: how many handles we were able to harvest for the account.
- `fully_explored` and `cutoff_reached`: whether we exhausted the modal or stopped early.
- `notes` and `error`: capture page-level hints such as protected accounts, empty lists, or collection exceptions.

This metadata makes it easy to identify private profiles, suspended accounts, or empty audiences even when no new edges are produced.

## JSON output
Calling `build_follower_graph` returns a `FollowerGraphResult`. Serialise it with `export_follower_graph_json`, which is now invoked automatically by the CLI. The payload contains:
- `start_handle`, `generated_at`, and `settings` (max layers and follower cap)
- `summary` with counts of visited nodes, total edges, and which handles were truncated
- `nodes`: the full list of `AccountTraversalRecord` entries
- `edges`: tuples of follower relationships (`source` follows `target`)

Example snippet:
```json
{
  "start_handle": "example",
  "summary": {
    "visited": 12,
    "edges": 48,
    "truncated_nodes": ["high_volume_account"]
  }
}
```

The CLI writes `follower_graph.csv` for edge lists and `follower_graph.json` for rich metadata. Custom paths can be supplied with `--output` (CSV) and `--output-json` (JSON).

## Optional prioritisation hook
Some investigations benefit from reordering the crawl when a follower list is truncated (for instance, prioritising known handles B and C before revisiting a high-volume account A). Pass a callback via `prioritize_on_truncation` to `build_follower_graph` to inject your own queue strategy:

```python
from weBot.workflows.follower_graph import build_follower_graph

WATCHLIST = {"acct_b", "acct_c"}

def focus_known_handles(handle, collection, depth):
  return [h for h in collection.followers if h in WATCHLIST]

result = build_follower_graph(
    bot,
    "seed_handle",
    max_layers=3,
    max_per_user=25,
    prioritize_on_truncation=focus_known_handles,
)
```

The callback receives the current handle, the `FollowerCollectionDetails` describing what was gathered, and the depth. Return an iterable of handles to push to the front of the queue. If omitted, traversal stays breadth-first.

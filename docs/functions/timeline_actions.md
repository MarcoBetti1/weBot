# Timeline Actions (weBot/core/actions/timeline.py)

## `scroll(driver, context)`
- **Purpose:** Advance to the next visible post while keeping the feed metadata up to date.
- **How it works:**
  1. Identifies the currently centred post and locates its successor in the DOM.
  2. If no successor exists, scrolls toward the bottom to trigger lazy loading, refreshes the post cache, and retries.
  3. Scrolls the target post into view, increments `context.post_index`, and calls `refresh_feed` to capture the latest article list.
- **Failure modes:** Returns an `ActionResult` with `success=False` when no further posts exist or a timeout/driver error occurs.

## `refresh_feed(driver, context)`
- **Goal:** Recalculate the number of loaded posts after any scroll or mutation.
- **Behaviour:** Invokes `update_post_cache`, stores `post_count` in the session attributes, and clamps `context.post_index` so the bot never points beyond the available list.

## `like(driver)`
- Clicks the centred post's like button. Uses a JS-first strategy with a Selenium fallback for reliability.

## `repost(driver, *, quote=None)`
- **Without `quote`:** Opens the repost dialog and confirms the repost button.
- **With `quote`:** Opens the quote composer, types the provided text, and submits the post.

## `quote(driver, text)`
- Convenience wrapper that forwards to `repost(..., quote=text)`. Exposed for clarity at the controller/session level.

## `reply(driver, text)` / `comment(driver, text)`
- Opens the reply dialog, types `text`, and sends it. `comment` simply proxies to `reply` so callers can use colloquial terminology.

## `bookmark(driver)`
- Clicks the bookmark button on the centred post.

## `update_post_cache(driver, context)`
- Waits for at least one article element, stores the current count, and returns the list of elements. Typically used internally by `refresh_feed`.

## `describe_center_post(driver)`
- Returns a short string (`"username: snippet"`) describing the currently selected post, helping CLI callers display context before interacting.

## `go_to_top(driver)`
- Scrolls the viewport to the top of the timeline after navigation.

## `create_post(driver, text)`
- Opens the composer, types `text`, and submits a new post. Handles common selector variants for the compose button and submit controls.

## Controller wrappers
- `BotController.like_center_post`, `repost_center_post`, `quote_center_post`, and `comment_on_center_post` call the corresponding action helpers after verifying a persisted profile is active.
- `BotController.make_post` publishes new posts via `create_post`.
- `BotController.selected_post_summary` exposes the CLI-friendly description from `describe_center_post`.

## Session commands
- The interactive `webot>` prompt exposes `home`, `like`, `repost [--quote]`, `quote --text`, `comment --text`, and `makepost --text`, each logging the outcome to the current session log.

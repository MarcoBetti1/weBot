# BotController Core Methods (weBot/bot.py)

## `manual_login(*, manual_timeout=600.0, persist_profile=True)`
- **Goal:** Hand off authentication to the operator while the bot watches for the home timeline.
- **Flow:**
  1. Sets the session login method to `manual`.
  2. Attempts to reuse an already-authenticated session by navigating to the home timeline.
  3. Navigates to the login page and polls for `PageState.HOME_TIMELINE`, printing state changes as they are detected.
  4. When successful, optionally calls `persist_profile()` to move any ephemeral Chrome profile into the persistent store.
- **Timeouts:** Accepts seconds or `None` for indefinite waiting. A non-positive value is interpreted as `None`.
- **Errors:** Raises `RuntimeError("Driver not started")` if `start()` was not called, and `RuntimeError` if the manual login deadline expires.

## `persist_profile()`
- **Goal:** Ensure the current Chrome user data directory survives after the session.
- **Behaviour:** Delegates to `DriverManager.persist_profile()` and prints the resolved path when available. Returns `Path | None`.

## Navigation Helpers (`go_home`, `navigate`, `ensure_home`)
- Each helper first calls `_require_persisted_profile()`; automation only proceeds when a saved profile is active.
- They update `SessionContext` with the latest `PageState` and mark the session as `logged_in` once `HOME_TIMELINE` is detected.
- **`go_home()`**: Uses `navigation.navigate_to` with `home_url`, returns the detected `PageState`.
- **`navigate(url)`**: General navigation wrapper returning the `ActionResult` from `navigation.navigate_to`.
- **`ensure_home()`**: Uses `navigation.ensure_state` to land on the home timeline if not already present.
- **Errors:** `_require_persisted_profile()` raises `RuntimeError` instructing the user to run `manual_login()` first when invoked without a saved profile.

## Timeline Interaction Helpers
- `like_center_post()` – likes the centred post.
- `bookmark_center_post()` – bookmarks the centred post.
- `repost_center_post(quote=None)` – reposts the centred post, optionally with a quote.
- `quote_center_post(text)` – convenience wrapper for quoting with text.
- `reply_to_center_post(text)` / `comment_on_center_post(text)` – submit a reply/comment with the provided text.

All helpers verify the session is using a persisted profile before interacting with the page.

## Guard `_require_persisted_profile()`
- Centralises the invariant that workflows must reuse a stored Chrome profile.
- Prevents accidental automation against a transient or anonymous browser session.

### State Tracking
- `SessionContext.logged_in` flips to `True` whenever the bot confirms the home timeline, allowing downstream logic or status commands to inspect the current authentication state.

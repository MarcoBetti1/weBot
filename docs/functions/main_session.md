# Session Orchestration (main.py)

## `_run_session(bot, *, default_manual_timeout)`
- **Purpose:** Launches an interactive REPL that keeps a single Selenium session alive while you issue commands.
- **Inputs:**
  - `bot`: a started `BotController` instance.
  - `default_manual_timeout`: timeout propagated to the inline `login` command; `None` means wait indefinitely.
- **Behaviour:**
  - Creates `logs/session-<UTC timestamp>.log` and shows the path to the user.
  - Delegates to `_session_loop` for the interactive prompt.
  - Ensures logging handlers are cleaned up even if an exception is raised.
- **Side effects:** creates the `logs/` directory if missing and writes log entries for every command.

## `_session_loop(bot, logger, default_manual_timeout)`
- **Purpose:** Implements the `webot>` prompt, parsing and executing commands until exit.
- **Key commands:** `login`, `engage`, `profile`, `follower-graph`, `navigate`, `like`, `repost`, `quote`, `comment`, `go-home`, `status`, `help`, `exit`/`quit`.
- **Error handling:**
  - Wraps every command execution in a `try/except`; on failure it prints `[error] <message>` and records `logger.exception` for full stack traces.
  - Ignores empty input and handles `Ctrl+C` (`KeyboardInterrupt`) without terminating the session.
- **Logging:**
  - Logs each command with its parsed arguments.
  - Logs success summaries (e.g., posts processed, handle targeted).
  - Logs warnings/errors for exceptions raised by underlying workflows.

## `_execute_workflow(bot, command, options)`
- **Purpose:** Runs non-login workflows (`engage`, `profile`, `follower-graph`) in both CLI and interactive contexts.
- **Steps:**
  1. Calls `_ensure_authenticated` to verify the active Chrome profile is persisted and on the home timeline.
  2. Executes the requested workflow and prints concise completion messages.
  3. Raises `ValueError` for unsupported commands so the caller can surface a clean parser error.
- **Common failures:** missing `--handle`, unauthenticated profile, Selenium navigation errors. These propagate back to the caller and are logged by the session loop if executed interactively.

## `_ensure_authenticated(bot)`
- **Purpose:** Safety gate prior to running any automated workflow.
- **Checks:**
  - Confirms the driver is backed by a persisted profile (`bot.profile_is_persistent`).
  - Calls `bot.ensure_home()` and expects `PageState.HOME_TIMELINE`.
- **Raises:** `RuntimeError` with actionable messages when the profile is absent or not logged in.

### Logging Conventions
- Log level `INFO` is used for command boundaries and normal completions.
- Unexpected exceptions result in `ERROR` log entries with stack traces.
- All timestamps are recorded in UTC using the format `YYYY-MM-DD HH:MM:SS,mmm`.

## Session logging helpers
- `_init_session_logger()` creates `logs/session-<timestamp>.log`, configures an isolated logger (`webot.session`), and prevents propagation to global handlers.
- `_teardown_session_logger()` closes and removes all session handlers to avoid duplicate log entries across successive sessions.

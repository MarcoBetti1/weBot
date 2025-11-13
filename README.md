## weBot (2025 refresh) untested

This repository hosts an experimental Selenium automation harness for Twitter/X.
The 2025 refresh focuses on observability and deterministic workflows so the
bot always knows which page state it is operating in. The codebase ships with a
state-driven action layer, testable “brains”, and high-level workflows for
timeline engagement, profile scraping, and follower graph crawling. **Automated
credential login has been removed**—you must sign in manually once, save the
Chrome profile, and reuse that profile for every subsequent workflow.

⚠️ **Twitter automation may violate the platform’s Terms of Service. Use at
your own risk and only against accounts you own or have explicit permission to
experiment with.**

## Project layout

```
weBot/
        core/          # Driver factory, state models, page recognisers, Selenium actions
        workflows/     # Manual-first workflows (profile fetch, follower graph, etc.)
        brains/        # Decision-making logic (scoring, interaction policy)
        data/          # Extractors and persistence helpers
        config/        # Optional environment helpers
bot.py           # High-level BotController orchestrating the pieces above
```

Legacy modules such as `scripts/` and `weBot/util.py` intentionally raise
`ImportError` so callers migrate to the new packages.

## Quick start

1. **Create and activate a virtual environment** (Python 3.10+ recommended).

        ```bash
        python3 -m venv .venv
        source .venv/bin/activate
        ```

2. **Install dependencies.**

        ```bash
        pip install -r requirements.txt
        ```

3. **Capture an authenticated Chrome profile via manual login.**

        ```bash
        python -m main login --fresh-profile --manual-timeout 0
        ```

        The CLI launches Chrome, navigates to the Twitter login page, and waits for
        the home timeline. Complete every authentication step yourself (password,
        challenges, 2FA, etc.). Once the timeline loads the bot marks the session as
        logged in and persists the profile directory. The console prints the saved
        profile path (for example `.webot/profiles/profile-20251112-102030`). Keep
        that path safe—it is required for every future workflow run.

4. **Reuse the saved profile for automation.**

        ```bash
        python -m main engage --chrome-profile .webot/profiles/profile-20251112-102030 --posts 5
        python -m main follower-graph --chrome-profile .webot/profiles/profile-20251112-102030 --handle jack --layers 2
        python -m main profile --chrome-profile .webot/profiles/profile-20251112-102030 --handle jack --descriptive
        ```

        All non-login commands require `--chrome-profile` (or a config file that
        provides the same value). The bot refuses to run workflows unless it can
        detect a persisted profile that is already authenticated.

### Interactive session mode

For exploratory testing you can keep a single Selenium session alive and run
multiple commands without restarting Chrome:

```bash
python -m main session --chrome-profile .webot/profiles/profile-20251112-102030
```

The program opens the browser, then presents a `webot>` prompt. Available
commands include `login`, `engage`, `profile`, `follower-graph`, `home`,
`like`, `repost`, `quote`, `comment`, `makepost`, `go-home`, `navigate`,
`status`, and `exit`. Run
`help` inside the prompt for full usage.
When launching the session without `--chrome-profile`, execute `login` first to
complete manual authentication and persist the profile for reuse.

During an interactive session, every command and error is recorded in a timestamped
log under `logs/`. Inspect that file when diagnosing Selenium edge cases or
workflow failures.

### Manual login notes

- `login` is the only command that touches authentication. It **never** enters
    credentials automatically; you do every step in the browser window.
- Pass `--manual-timeout <seconds>` if you want an upper bound on how long the
    CLI waits for the home timeline. Use `--manual-timeout 0` to wait forever.
- Combine `--fresh-profile` with `--profiles-root /absolute/path` to store
    saved profiles outside the repository. If you omit `--fresh-profile`, the
    login command uses a temporary profile that is persisted only after the home
    timeline appears.
- To reuse an existing profile without logging in again, supply
    `--chrome-profile <path>` to the login command; the CLI will detect that the
    session is already authenticated and simply confirm it.

### Running workflows from config files

You can store CLI options in JSON or YAML and load them with `@config` syntax.

```yaml
# config.yaml
command: profile
chrome_profile: .webot/profiles/profile-20251112-102030
handle: jack
descriptive: true
```

Invoke it with `python -m main @config.yaml`. Command-line arguments override
values from the file when both are provided.

## Key details

- **State awareness:** Every action is guarded by `PageState` detection so the
    bot only interacts with pages it recognises.
- **Manual-first session management:** Workflows verify that a persisted Chrome
    profile is loaded before executing. If the profile is missing or logged out,
    the CLI aborts with an actionable error.
- **Composable actions:** Low-level interactions (scrolling, liking, follower
    harvesting) live in dedicated modules and remain individually testable.
- **Brains rework:** Sentiment scoring and rate limiting stay pure functions,
    enabling unit tests without Selenium.
- **Per-session logging:** Interactive sessions create `logs/session-*.log`
    files capturing commands, parameters, and stack traces for debugging.

## Function reference

Detailed Markdown notes live under `docs/functions/`, covering the behaviour,
inputs, outputs, and failure modes of the key functions (`BotController`
helpers, session orchestration, follower graph traversal, and social data
extraction). Review these files when extending or testing specific routines.

## Troubleshooting

- **`A saved Chrome profile is required`** – run the login command first, allow
    it to persist the profile, then pass that path via `--chrome-profile`.
- **`The provided Chrome profile is not authenticated`** – open the profile in
    Chrome manually, confirm you can access the home timeline, or run the login
    command again to refresh cookies and security tokens.
- **Chrome prompts for “browser is not secure”** – create a fresh profile with
    `--fresh-profile` and optionally customise `--user-agent` to mimic your daily
    browser.
- **Profile path clutter** – delete old entries under `.webot/profiles/` once
    you no longer need them; the bot only uses the path you pass on the CLI.

## Next steps

- Improve profile health checks (detect lockouts, expired sessions).
- Keep iterating on human-like delays to dodge bot protection.

## weBot (2025 refresh) untested

This repository hosts an experimental Selenium automation harness for Twitter/X.
The 2025 refresh focuses on observability and deterministic workflows so the
bot always knows which page state it is operating in.  It now ships with a
state-driven action layer, testable “brains”, and high-level workflows for
login, timeline engagement, profile scraping, and follower graph crawling.

⚠️ **Twitter automation may violate the platform’s Terms of Service.  Use at
your own risk and only against accounts you own or have explicit permission
to experiment with.**

## Project layout

```
weBot/
    core/          # Driver factory, state models, page recognisers, Selenium actions
    workflows/     # Composable workflows (login, profile fetch, follower graph)
    brains/        # Decision-making logic (scoring, interaction policy)
    data/          # Extractors and persistence helpers
    config/        # Environment loading and examples
bot.py           # High-level BotController orchestrating the pieces above
```

Legacy modules under `scripts/` and `weBot/util.py` now intentionally raise
`ImportError`. Update existing projects to import from the packages above.

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

3. **Provide credentials** in a `.env` file (never commit this!). Supply any
    identifiers you have—username, email, or phone—and the bot will cycle
    through them when the login form resets. If you rely on Google or Apple SSO
    you still need to launch the flow manually, but the CLI can open the right
    button for you.  Each run defaults to an isolated Chrome profile so cached
    data and stale security prompts are cleared automatically. The automation
    layer now applies stealth tweaks (e.g., masking `navigator.webdriver`) to
    look more like a real browser session.
     ```env
     WEBOT_USERNAME=your_username
     WEBOT_PASSWORD=your_password
     WEBOT_EMAIL=optional_email_used_for_challenges
    WEBOT_PHONE=optional_phone_number
     ```

4. **Run a task via the CLI** (flags or config file).
     ```bash
    python -m main login
    python -m main engage --posts 5
    python -m main follower-graph --handle jack --layers 2 --output jack_graph.csv
    python -m main profile --handle jack --output jack_profile.json --descriptive
     ```

    The browser launches in non-headless mode by default. Use `--headless` for
    CI. Add `--login-order username,email,phone` to override identifier
    rotation, `--login-method google` (or `apple`) to pop the OAuth window,
    `--login-method manual` to drive the browser yourself while the bot waits,
    `--fresh-profile` to mint a brand-new Chrome profile under `.webot/profiles`
    (override the root with `--profiles-root /path`), `--chrome-profile
    /existing/user-data` to reuse one you trust, `--user-agent "..."` to spoof
    the UA string, `--no-ephemeral-profile` to disable temporary profile
    creation, `--manual-timeout 0` to wait indefinitely for manual login,
    `--preserve-profile` to keep any temporary profile that was created, and
    `--no-cookies` to force a fresh credential login. You can also store these
    options in a config file:

    ```yaml
    # config.yaml
    command: engage
    chrome_profile: .webot/profiles/profile-20251112-0137223dq7k09e
    no_ephemeral_profile: true
    posts: 5
    cookies: cookies.json
    ```

    Then run with `python -m main @config.yaml` (or `@config.json`). Values in
    the file behave the same as CLI flags; command-line arguments override the
    file.

### Minting a fresh Chrome profile

Running `python -m main login --fresh-profile` will create a timestamped user
data directory under `.webot/profiles/` and print its location. That directory
persists after the run so you can inspect or reuse it manually. To organise
profiles elsewhere, pass `--profiles-root /absolute/path`. Pairing
`--fresh-profile` with a custom `--user-agent` often helps bypass the “browser
is not secure” dialog on Google sign-in.

## Key improvements

- **State awareness:** The bot continuously classifies the current page into a
    `PageState` enum before executing any action, avoiding mismatched clicks.
- **Composable actions:** Low-level interactions (login steps, scrolling,
    liking, follower harvesting) live in dedicated modules that can be imported
    and tested individually.
- **Workflow engine:** Workflows (login, follower graph crawl, etc.) are driven
    by a finite-state engine that retries deterministically and bubbles up
    actionable errors.
- **Brains rework:** Sentiment scoring and rate limiting are pure functions, so
    you can unit-test the engagement logic without Selenium.
- **Environment hygiene:** Credentials are loaded via `.env`/environment
    variables and persisted cookies move to `cookies.json`. The old
    compatibility modules now raise errors so callers migrate to the new API.
- **OAuth & manual helpers:** Optional `--login-method google|apple` clicks the
    provider button and waits for you to finish the hand-off, capturing cookies
    once the home timeline loads. If the button cannot be located, the bot now
    falls back to `manual` mode automatically and keeps the window ready for
    you to complete login yourself.

### Manual login workflow

If the automated selectors fail or you simply prefer to sign in manually, run:

```bash
python -m main login --login-method manual --fresh-profile --manual-timeout 0 --preserve-profile
```

The CLI opens Chrome at the Twitter login page, prints the active profile path,
and watches for the home timeline. Complete the login in the browser; once the
timeline appears the bot saves cookies (default `cookies.json`) and, if you
requested profile preservation, moves the Chrome user data directory under
`.webot/profiles/` for future runs. Subsequent commands (for example
`python -m main engage`) will first attempt to restore those cookies, reporting
how many were loaded before continuing. The engagement flow now skips redundant
refreshes when it detects the home timeline, making the hand-off from manual
login to automation seamless. Adjust `--manual-timeout` to cap the wait window
or leave it at `0` for an unlimited session.

## Troubleshooting login

- **"Could not log you in now." toast** – the login workflow detects this and
    will retry the next identifier once. After a full cycle it exits with the
    server message so you can switch to Google/Apple or wait out rate limits.
- **OAuth stalls** – the automation cannot pass the two-factor / captcha steps
    for providers. Use the CLI to open the Google/Apple window, finish the flow
    manually (the bot now reports missing buttons and automatically switches to
    manual mode), and it will save cookies for future runs.
- **Manual login blocked** – rotate IPs or wait; saving cookies after a
    successful session is the safest mitigation.
- **Chrome says “browser is not secure”** – launch with the default ephemeral
    profile (no flags), or delete the generated profile directory. If you need
    persistence, mint a new one via `--fresh-profile` (optionally overriding the
    root) or point `--chrome-profile` at a clean user data folder and combine it
    with `--user-agent` to mimic your daily driver. Pairing the run with
    `--no-ephemeral-profile` ensures the chosen directory is reused as-is.

## Next steps

- Harden login strategy (detect more error banners, smarter pacing).
- Keep iterating on human-like delays to dodge bot protection.

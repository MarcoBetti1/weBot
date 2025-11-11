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
   through them when the login form resets.
     ```env
     WEBOT_USERNAME=your_username
     WEBOT_PASSWORD=your_password
     WEBOT_EMAIL=optional_email_used_for_challenges
    WEBOT_PHONE=optional_phone_number
     ```

4. **Run a task via the CLI.**
     ```bash
    python -m main login
     python -m main engage --posts 5
     python -m main follower-graph --handle jack --layers 2 --output jack_graph.csv
     python -m main profile --handle jack --output jack_profile.json --descriptive
     ```

    The browser launches in non-headless mode by default. Use `--headless` for
    CI or `--login-order username,email,phone` to override the identifier
    rotation. Add `--no-cookies` to force a fresh credential login.

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

## Next steps

- Test if this shit works
    - Shit dont work, ip block or something. Login with google or apple.
- Make em think its human

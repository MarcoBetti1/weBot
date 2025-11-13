# Behaviour Configuration

The behaviour subsystem centralises every human-like delay used by the automation stack. Runtime modules call `weBot.config.behaviour.get_behaviour_settings()` to retrieve the active configuration, so changing a single YAML or JSON document updates typing cadence, generic waits, and named delay ranges across the entire bot.

## Loading Rules

- **Default search paths:** `weBot/config/behavior.yaml` or `weBot/config/behaviour.yaml` relative to your current working directory. Copy `weBot/config/behavior.example.yaml` to one of those paths to get started.
- **CLI override:** pass `--behavior-config <path>` to any `python -m main ...` invocation (including `session`) to point at a file in a custom location.
- **Supported formats:** YAML and JSON. YAML files require the `PyYAML` dependency, already listed in `requirements.txt`.
- **Error handling:** if the loader cannot parse the file it now raises a `RuntimeError` describing the failing path and error message instead of silently falling back to defaults.
- **Fallback behaviour:** when no configuration file is found or provided, the built-in defaults from `BehaviourSettings` apply.

## Top-Level Fields

| Key                 | Type                     | Description |
|---------------------|--------------------------|-------------|
| `typing_delay`      | object `{min, max}`      | Random delay range (seconds) between keystrokes; also honoured by `human_type` fallthrough delays. |
| `random_delay`      | object `{min, max}`      | Default range for `random_delay()` whenever no explicit min/max is supplied. |
| `micro_wait`        | object `{min, max}`      | Range used by `micro_wait()` and as the `micro_wait` named override. |
| `navigation_wait`   | number                   | Fixed pause (seconds) after `driver.get()` before the state recogniser runs. |
| `post_pause_seconds`| number                   | Sleep between timeline posts when running `engage` flows. |
| `loop.error_pause`  | number                   | Back-off interval after errors inside loop scripts. |
| `loop.cycle_pause`  | object `{min, max}`      | Delay range between loop iterations. |
| `named_ranges`      | object of `{min, max}`   | Optional labelled ranges that actions can request via `random_delay(label="your_label")`. |

Numbers can be integers or floats; the loader normalises them to floats and swaps `min`/`max` automatically if the values are inverted.

## Named Ranges

Several action modules request labelled delays to better describe their context. When a label is missing from the config the code falls back to `random_delay`. The bundled example defines the following labels:

- `pause_short` – lightweight pauses before or after small UI interactions.
- `pause_medium` – used during modal transitions such as repost confirmations.
- `pause_long` – applied to slower navigation like opening author profiles.
- `pause_medium_long` – follows follow/unfollow interactions.
- `menu_pause` – spacing between menu clicks inside dropdowns.
- `scroll_settle` – wait after scrolling to the next post.
- `scroll_fetch` – delay applied when fetching additional timeline content.
- `profile_fetch` – pacing for profile and follower list loading.
- `micro_wait` – already wired to `micro_wait()` to keep very short waits adjustable.

Feel free to add more labels; they become available immediately without code changes.

## Example YAML

```yaml
# config/behavior.yaml
typing_delay:
  min: 0.25
  max: 0.9

random_delay:
  min: 1.0
  max: 2.5

navigation_wait: 1.5
post_pause_seconds: 1.2

named_ranges:
  pause_short:
    min: 0.4
    max: 0.7
  composer_think:
    min: 1.5
    max: 2.8
```

This configuration slows typing to roughly one character every quarter second, increases the base delay between posts, and introduces a custom `composer_think` label you can reference from new automation routines.

## Troubleshooting

- **`Failed to load behaviour configuration`** – check the file path, ensure the content is valid YAML/JSON, and confirm `PyYAML` is installed when using YAML.
- **Delays did not change** – confirm the session was launched with the right `--behavior-config` path and that no other run overrides it later; the active settings are captured when the CLI starts.
- **Need to reset to defaults** – remove or rename the behaviour file, or delete any labels you no longer want. The loader will fall back to the baked-in defaults when it cannot find a config file.

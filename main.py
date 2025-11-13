"""CLI entrypoint for the restructured weBot automation framework."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Set

from weBot.bot import BotController
from weBot.brains.engage import process_feed
from weBot.config.settings import load_credentials
from weBot.data.graph_io import export_edges_to_csv
from weBot.data.storage import save_json
from weBot.workflows import follower_graph as follower_workflow
from weBot.workflows.profile import fetch_profile


COMMAND_CHOICES = ("login", "engage", "follower-graph", "profile")


def _load_config_file(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        return {}

    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("PyYAML is required to load YAML config files") from exc
        data = yaml.safe_load(text) or {}
    else:
        data = json.loads(text)

    if not isinstance(data, dict):
        raise ValueError("Configuration file must define a JSON/YAML object at the top level")
    return data


def _collect_cli_overrides(argv: Iterable[str]) -> Set[str]:
    overrides: Set[str] = set()
    argv_list = list(argv)
    for index, token in enumerate(argv_list):
        if token == "--":
            break
        if token.startswith("--"):
            name = token[2:]
            if not name:
                continue
            if "=" in name:
                name = name.split("=", 1)[0]
            overrides.add(name.replace("-", "_"))
            if "=" not in token and index + 1 < len(argv_list):
                next_token = argv_list[index + 1]
                if not next_token.startswith("--"):
                    # skip value token
                    continue
        else:
            if index == 0:
                overrides.add("command")
    return overrides


PATH_KEYS = {
    "chrome_profile",
    "profiles_root",
    "cookies",
    "output",
    "env_file",
}


def _apply_config(
    args: argparse.Namespace,
    config: Dict[str, Any],
    *,
    overrides: Set[str],
    base_dir: Path | None = None,
) -> argparse.Namespace:
    for raw_key, value in config.items():
        key = raw_key.replace("-", "_")
        if not hasattr(args, key):
            continue
        if key == "config" or key == "config_file":
            continue
        if key == "command":
            if "command" not in overrides and getattr(args, "command", None) in (None, ""):
                setattr(args, "command", value)
            continue
        if key in overrides:
            continue
        if base_dir and key in PATH_KEYS and isinstance(value, str):
            value = str((base_dir / value).expanduser())
        setattr(args, key, value)
    return args


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automation toolkit for Twitter/X interactions")
    parser.add_argument("command", nargs="?", choices=COMMAND_CHOICES, help="Task to run")
    parser.add_argument("--config", dest="config_file", help="Path to YAML or JSON config with CLI options")
    parser.add_argument("--env", dest="env_file", default=None, help="Path to .env file with credentials")
    parser.add_argument("--cookies", dest="cookies", default="cookies.json", help="Location for persisted cookies")
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode")
    parser.add_argument("--no-cookies", action="store_true", help="Skip attempting cookie-based login")
    parser.add_argument("--posts", type=int, default=10, help="Number of timeline posts to process (for engage)")
    parser.add_argument("--handle", help="Target handle for follower graph or profile commands")
    parser.add_argument("--layers", type=int, default=3, help="Depth for follower graph BFS")
    parser.add_argument("--max-per-user", type=int, default=40, help="Follower cap per user when crawling")
    parser.add_argument("--output", help="Optional file output (JSON or CSV depending on command)")
    parser.add_argument("--descriptive", action="store_true", help="Include follower/following lists when fetching profile data")
    parser.add_argument(
        "--login-order",
        dest="login_order",
        default=None,
        help="Comma-separated priority of identifiers to try (any combination of username,email,phone)",
    )
    parser.add_argument(
        "--login-method",
        dest="login_method",
        default="auto",
        choices=["auto", "credentials", "google", "apple", "manual"],
        help="Select the login method: credentials, Google, Apple, or manual",
    )
    parser.add_argument(
        "--chrome-profile",
        dest="chrome_profile",
        help="Path to a Chrome user data directory to reuse between runs",
    )
    parser.add_argument(
        "--no-ephemeral-profile",
        dest="no_ephemeral_profile",
        action="store_true",
        help="Disable creation of a fresh temporary Chrome profile for this run",
    )
    parser.add_argument(
        "--fresh-profile",
        dest="fresh_profile",
        action="store_true",
        help="Automatically mint a brand-new Chrome profile under the profiles root and use it for this run",
    )
    parser.add_argument(
        "--profiles-root",
        dest="profiles_root",
        help="Directory where --fresh-profile should create Chrome user data folders (default: .webot/profiles)",
    )
    parser.add_argument(
        "--user-agent",
        dest="user_agent",
        help="Override the browser user agent string to evade bot detection",
    )
    parser.add_argument(
        "--manual-timeout",
        dest="manual_timeout",
        type=float,
        default=600.0,
        help="Seconds to wait for manual login before aborting (0 or negative for unlimited)",
    )
    parser.add_argument(
        "--preserve-profile",
        dest="preserve_profile",
        action="store_true",
        help="Keep the Chrome profile directory after a successful login for reuse",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv_list = list(argv) if argv is not None else sys.argv[1:]
    parser = _build_parser()
    args = parser.parse_args(argv_list)

    cli_overrides = _collect_cli_overrides(argv_list)
    if args.config_file:
        config_path = Path(args.config_file).expanduser()
        config_values = _load_config_file(config_path)
        args = _apply_config(args, config_values, overrides=cli_overrides, base_dir=config_path.parent)

    if args.command is None:
        parser.error("A command must be provided via CLI or --config")

    if args.command not in COMMAND_CHOICES:
        parser.error(f"Unknown command {args.command}")

    if args.command in {"follower-graph", "profile"} and not args.handle:
        parser.error("--handle is required for follower-graph and profile commands")

    if args.chrome_profile and args.fresh_profile:
        parser.error("--fresh-profile cannot be combined with --chrome-profile")

    if args.manual_timeout is not None and args.manual_timeout < 0:
        manual_timeout = None
    else:
        manual_timeout = args.manual_timeout

    credentials = load_credentials(Path(args.env_file) if args.env_file else None)

    from weBot.core.driver import DriverConfig

    user_data_dir = Path(args.chrome_profile).expanduser() if args.chrome_profile else None
    profiles_root = Path(args.profiles_root).expanduser() if args.profiles_root else None
    use_ephemeral_profile = not args.no_ephemeral_profile and not args.fresh_profile and user_data_dir is None
    driver_config = DriverConfig(
        headless=args.headless,
        user_data_dir=user_data_dir,
        use_ephemeral_profile=use_ephemeral_profile,
        bootstrap_profile=args.fresh_profile,
        profile_root=profiles_root,
        user_agent=args.user_agent,
    )
    identifier_priority = None
    if args.login_order:
        allowed_tokens = {"username", "email", "phone"}
        raw_tokens = [part.strip().lower() for part in args.login_order.split(",") if part.strip()]
        invalid = [token for token in raw_tokens if token not in allowed_tokens]
        if invalid:
            parser.error(f"Unsupported login identifiers in --login-order: {', '.join(invalid)}")
        identifier_priority = raw_tokens or None

    bot = BotController(
        username=credentials.username,
        password=credentials.password,
        email=credentials.email,
        phone=credentials.phone,
        identifier_priority=identifier_priority,
        driver_config=driver_config,
        cookies_path=Path(args.cookies),
    )

    bot.start()

    if bot.profile_path:
        label = "Fresh Chrome profile" if args.fresh_profile and not args.chrome_profile else "Chrome profile"
        print(f"{label}: {bot.profile_path}")

    try:
        prefer_cookies = not args.no_cookies
        login_method = args.login_method or "auto"
        preserve_profile_flag = args.preserve_profile or (login_method == "manual")
        if login_method == "credentials":
            login_method = "auto"
        final_state = bot.login(
            prefer_cookies=prefer_cookies,
            method=login_method,
            manual_timeout=manual_timeout,
            preserve_profile=preserve_profile_flag,
        )
        if final_state != bot.context.current_state:
            bot.context.update_state(final_state)

        if args.command == "login":
            print(f"Login completed with state: {final_state.name}")
            return 0

        if args.command == "engage":
            bot.ensure_home()
            process_feed(bot, posts=args.posts)
            return 0

        if args.command == "follower-graph":
            result = follower_workflow.build_follower_graph(
                bot,
                args.handle,
                max_layers=args.layers,
                max_per_user=args.max_per_user,
            )
            output = args.output or "follower_graph.csv"
            export_edges_to_csv(result.edges, filename=output)
            print(f"Follower graph exported to {output}")
            return 0

        if args.command == "profile":
            profile = fetch_profile(bot, args.handle, descriptive=args.descriptive)
            profile_data = asdict(profile)
            if args.output:
                output_path = Path(args.output)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_text(json.dumps(profile_data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"Profile saved to {output_path}")
            else:
                path = save_json(args.handle, profile_data)
                print(f"Profile saved to {path}")
            return 0

        parser.error(f"Unknown command {args.command}")
    finally:
        bot.stop()

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())

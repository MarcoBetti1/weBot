"""CLI entrypoint for the restructured weBot automation framework."""
from __future__ import annotations

import argparse
import json
import logging
import shlex
import sys
from datetime import datetime
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Iterable, Set
SESSION_LOGGER_NAME = "webot.session"


from weBot.bot import BotController
from weBot.brains.engage import process_feed
from weBot.core.state import PageState
from weBot.data.storage import save_json
from weBot.workflows.profile import fetch_profile
from weBot.config.behaviour import load_behaviour_settings, set_behaviour_settings
from weBot.core.driver import DriverConfig, validate_profile_name


COMMAND_CHOICES = ("login", "engage", "profile", "session")


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
    "profiles_root",
    "output",
    "behavior_config",
}


def _resolve_profiles_root(raw: str | None) -> Path:
    root = Path(raw).expanduser() if raw else Path(".webot/profiles")
    root = root.absolute()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _profile_alias_to_path(alias: str, *, profiles_root: Path) -> Path:
    normalized = validate_profile_name(alias)
    return (profiles_root / normalized).expanduser().absolute()


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
    parser.add_argument("--headless", action="store_true", help="Run the browser in headless mode")
    parser.add_argument("--posts", type=int, default=10, help="Number of timeline posts to process (for engage)")
    parser.add_argument("--handle", help="Target handle for profile commands")
    parser.add_argument("--output", help="Optional file output (JSON or CSV depending on command)")
    parser.add_argument("--descriptive", action="store_true", help="Include follower/following lists when fetching profile data")
    parser.add_argument(
        "--chrome-profile",
        dest="chrome_profile",
        help="Saved Chrome profile name to reuse between runs",
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
        "--profile-name",
        dest="profile_name",
        help="Friendly name to assign when persisting a Chrome profile (login only)",
    )
    parser.add_argument(
        "--behavior-config",
        dest="behavior_config",
        help="Path to YAML or JSON file overriding human-like timing defaults",
    )
    return parser


def _ensure_authenticated(bot: BotController) -> None:
    if not bot.profile_is_persistent:
        raise RuntimeError(
            "A saved Chrome profile is required. Run the login command first and reuse the persisted profile."
        )

    state = bot.ensure_home()
    if state != PageState.HOME_TIMELINE:
        raise RuntimeError(
            "The active Chrome profile is not authenticated. Complete manual login and try again."
        )


def _execute_workflow(bot: BotController, command: str, options: argparse.Namespace) -> None:
    _ensure_authenticated(bot)

    if command == "engage":
        posts = getattr(options, "posts", 10)
        process_feed(bot, posts=posts)
        print(f"Engaged with {posts} timeline posts.")
        return

    if command == "profile":
        profile = fetch_profile(bot, options.handle, descriptive=options.descriptive)
        profile_data = asdict(profile)
        if options.output:
            output_path = Path(options.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(json.dumps(profile_data, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Profile saved to {output_path}")
        else:
            path = save_json(options.handle, profile_data)
            print(f"Profile saved to {path}")
        return

    raise ValueError(f"Unsupported workflow command: {command}")


def _parse_session_command(
    line: str,
    *,
    default_manual_timeout: float | None,
) -> tuple[str | None, argparse.Namespace | None]:
    tokens = shlex.split(line)
    if not tokens:
        return None, None

    command = tokens[0].lower()
    args = tokens[1:]

    def build_parser(prog: str) -> argparse.ArgumentParser:
        return argparse.ArgumentParser(prog=prog)

    try:
        if command == "login":
            parser = build_parser("login")
            parser.add_argument("--manual-timeout", type=float, default=default_manual_timeout)
            parser.add_argument("--no-persist-profile", action="store_true")
            parser.add_argument("--profile-name")
            return command, parser.parse_args(args)

        if command == "engage":
            parser = build_parser("engage")
            parser.add_argument("--posts", type=int, default=10)
            return command, parser.parse_args(args)

        if command == "profile":
            parser = build_parser("profile")
            parser.add_argument("--handle", required=True)
            parser.add_argument("--output")
            parser.add_argument("--descriptive", action="store_true")
            return command, parser.parse_args(args)

        if command == "navigate":
            parser = build_parser("navigate")
            parser.add_argument("url")
            return command, parser.parse_args(args)

        if command == "home":
            parser = build_parser("home")
            return command, parser.parse_args(args)

        if command == "like":
            parser = build_parser("like")
            return command, parser.parse_args(args)

        if command == "repost":
            parser = build_parser("repost")
            parser.add_argument("--quote")
            return command, parser.parse_args(args)

        if command == "quote":
            parser = build_parser("quote")
            parser.add_argument("--text", required=True)
            return command, parser.parse_args(args)

        if command == "comment":
            parser = build_parser("comment")
            parser.add_argument("--text", required=True)
            return command, parser.parse_args(args)

        if command == "makepost":
            parser = build_parser("makepost")
            parser.add_argument("--text", required=True)
            return command, parser.parse_args(args)

        if command == "stop":
            parser = build_parser("stop")
            return command, parser.parse_args(args)

        if command == "loop":
            normalized = list(args)
            if not normalized:
                normalized = ["status"]
            elif normalized[0] not in {"start", "stop", "status", "list"}:
                normalized.insert(0, "start")

            parser = build_parser("loop")
            parser.add_argument("action", choices=["start", "stop", "status", "list"])
            parser.add_argument("script", nargs="?", help="Script name (required for start)")
            parser.add_argument("--posts-per-cycle", dest="posts_per_cycle", type=int, default=10)
            parser.add_argument("--iterations", dest="iterations", type=int)
            parser.add_argument("--min-delay", dest="min_delay", type=float)
            parser.add_argument("--max-delay", dest="max_delay", type=float)
            return command, parser.parse_args(normalized)

        if command in {"go-home", "status", "help", "exit", "quit"}:
            return command, argparse.Namespace()

        print("Unknown command. Type 'help' for available commands.")
        return None, None
    except SystemExit:
        # argparse already printed the error/help message
        return None, None


def _print_session_help() -> None:
    print(
        "Available commands:\n"
        "  login [--manual-timeout SECONDS] [--no-persist-profile]\n"
        "  engage [--posts N]\n"
    "  profile --handle NAME [--output PATH] [--descriptive]\n"
        "  navigate URL\n"
        "  home\n"
        "  like\n"
        "  repost [--quote TEXT]\n"
        "  quote --text TEXT\n"
        "  comment --text TEXT\n"
        "  makepost --text TEXT\n"
    "  loop [start] NAME [--posts-per-cycle N] [--iterations N] [--min-delay S] [--max-delay S]\n"
    "  loop stop | loop status | loop list\n"
    "  stop\n"
        "  go-home\n"
        "  status\n"
        "  help\n"
        "  exit | quit"
    )


def _run_session(bot: BotController, *, default_manual_timeout: float | None) -> None:
    log_path = _init_session_logger()
    logger = logging.getLogger(SESSION_LOGGER_NAME)
    print("Interactive session started. Type 'help' to list available commands.")
    print(f"Session log: {log_path}")
    try:
        _session_loop(bot, logger, default_manual_timeout)
    finally:
        _teardown_session_logger()


def _session_loop(bot: BotController, logger: logging.Logger, default_manual_timeout: float | None) -> None:
    while True:
        try:
            line = input("webot> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:  # pragma: no cover - interactive convenience
            print()
            continue

        if not line:
            continue

        command, options = _parse_session_command(line, default_manual_timeout=default_manual_timeout)
        if command is None:
            continue

        logger.info("Command received: %s %s", command, vars(options) if options else {})

        if bot.loop_manager.is_running() and command not in {"loop", "help", "status", "stop", "exit", "quit"}:
            print("A loop script is running. Stop it with 'loop stop' before executing other commands.")
            logger.warning("Command %s blocked because a loop script is active.", command)
            continue

        if command in {"exit", "quit"}:
            if bot.loop_manager.is_running():
                print("Stopping active loop before exiting...")
                bot.loop_manager.stop(wait=5.0)
            break

        if command == "help":
            _print_session_help()
            continue

        try:
            if command == "login":
                manual_timeout = options.manual_timeout
                if manual_timeout is not None and manual_timeout < 0:
                    manual_timeout = None
                state = bot.manual_login(
                    manual_timeout=manual_timeout,
                    persist_profile=not getattr(options, "no_persist_profile", False),
                    profile_name=getattr(options, "profile_name", None),
                )
                print(f"Manual login completed with state: {state.name}")
                logger.info("Manual login completed: state=%s", state.name)
                continue

            if command == "engage":
                _execute_workflow(bot, "engage", options)
                logger.info("Engage workflow finished (posts=%s).", getattr(options, "posts", 10))
                continue

            if command == "loop":
                action = options.action
                if action == "list":
                    scripts = bot.loop_manager.available_scripts()
                    if not scripts:
                        print("No loop scripts available.")
                    else:
                        print("Available loop scripts:")
                        for name, definition in sorted(scripts.items()):
                            print(f"  {name}: {definition.description}")
                    logger.info("Loop list displayed (count=%s).", len(scripts))
                    continue

                if action == "status":
                    status = bot.loop_manager.status()
                    if status["running"]:
                        print(f"Loop running: {status['script']}")
                    else:
                        print("No loop script is running.")
                    logger.info("Loop status queried; running=%s script=%s", status["running"], status["script"])
                    continue

                if action == "stop":
                    if bot.loop_manager.stop():
                        print("Loop stop requested.")
                        logger.info("Loop stop requested.")
                    else:
                        print("No active loop to stop.")
                        logger.info("Loop stop requested but no active script.")
                    continue

                script_name = options.script
                if not script_name:
                    print("Specify a script name, e.g. 'loop random_engage'. Use 'loop list' to see options.")
                    continue

                script_key = script_name.lower().replace("-", "_")
                _ensure_authenticated(bot)
                try:
                    bot.loop_manager.start(
                        script_key,
                        logger=logger,
                        posts_per_cycle=options.posts_per_cycle,
                        iteration_limit=options.iterations,
                        min_delay=options.min_delay,
                        max_delay=options.max_delay,
                    )
                except Exception as exc:  # pragma: no cover - interactive loop
                    print(f"Failed to start loop: {exc}")
                    logger.exception("Loop start failed for script=%s", script_key)
                else:
                    print(f"Loop script '{script_key}' started.")
                    logger.info(
                        "Loop script started; name=%s posts_per_cycle=%s iterations=%s min_delay=%s max_delay=%s",
                        script_key,
                        options.posts_per_cycle,
                        options.iterations,
                        options.min_delay,
                        options.max_delay,
                    )
                continue

            if command == "stop":
                if bot.loop_manager.stop():
                    print("Loop stop requested.")
                    logger.info("Loop stop requested via 'stop' command.")
                else:
                    print("No active loop to stop.")
                    logger.info("'stop' command issued with no active loop.")
                continue

            if command == "profile":
                _execute_workflow(bot, "profile", options)
                logger.info("Profile workflow finished for handle=%s.", options.handle)
                continue

            if command == "go-home":
                state = bot.go_home()
                print(f"Current state: {state.name}")
                logger.info("Go home executed; state=%s", state.name)
                continue

            if command == "navigate":
                result = bot.navigate(options.url)
                state = result.next_state or bot.context.current_state
                print(f"Navigated to {options.url} (state: {state.name})")
                logger.info("Navigate executed; url=%s state=%s", options.url, state.name)
                continue

            if command == "home":
                _ensure_authenticated(bot)
                state = bot.go_home()
                summary = bot.selected_post_summary()
                if summary:
                    print(f"At top of home timeline. Selected post: {summary}")
                else:
                    print("At top of home timeline.")
                logger.info("Home command executed; state=%s", state.name)
                continue

            if command == "like":
                _ensure_authenticated(bot)
                summary = bot.selected_post_summary()
                if summary:
                    print(f"Selected post: {summary}")
                success = bot.like_center_post()
                print("Like successful" if success else "Like failed")
                logger.info("Like command completed; success=%s", success)
                continue

            if command == "repost":
                _ensure_authenticated(bot)
                summary = bot.selected_post_summary()
                if summary:
                    print(f"Selected post: {summary}")
                success = bot.repost_center_post(quote=getattr(options, "quote", None))
                print("Repost successful" if success else "Repost failed")
                logger.info("Repost command completed; success=%s quote=%s", success, getattr(options, "quote", None))
                continue

            if command == "quote":
                _ensure_authenticated(bot)
                summary = bot.selected_post_summary()
                if summary:
                    print(f"Selected post: {summary}")
                success = bot.quote_center_post(options.text)
                print("Quote successful" if success else "Quote failed")
                logger.info("Quote command completed; success=%s", success)
                continue

            if command == "comment":
                _ensure_authenticated(bot)
                summary = bot.selected_post_summary()
                if summary:
                    print(f"Selected post: {summary}")
                success = bot.comment_on_center_post(options.text)
                print("Comment successful" if success else "Comment failed")
                logger.info("Comment command completed; success=%s", success)
                continue

            if command == "makepost":
                _ensure_authenticated(bot)
                success = bot.make_post(options.text)
                print("Post published" if success else "Failed to publish post")
                logger.info("MakePost command completed; success=%s", success)
                continue

            if command == "status":
                state = bot.context.current_state
                print(f"State: {state.name}")
                print(f"Logged in: {bot.context.logged_in}")
                print(f"Profile path: {bot.profile_path or 'None'} (persistent={bot.profile_is_persistent})")
                logger.info("Status queried; state=%s logged_in=%s", state.name, bot.context.logged_in)
                continue

            print("Unknown command. Type 'help' for available commands.")
        except Exception as exc:  # pragma: no cover - interactive loop
            print(f"[error] {exc}")
            logger.exception("Command '%s' failed", command)


def _init_session_logger() -> Path:
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"session-{timestamp}.log"

    logger = logging.getLogger(SESSION_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return log_path


def _teardown_session_logger() -> None:
    logger = logging.getLogger(SESSION_LOGGER_NAME)
    for handler in list(logger.handlers):
        handler.close()
        logger.removeHandler(handler)


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

    if args.command == "profile" and not args.handle:
        parser.error("--handle is required for the profile command")

    profiles_root = _resolve_profiles_root(getattr(args, "profiles_root", None))

    behaviour_config_path: Path | None = None
    if getattr(args, "behavior_config", None):
        behaviour_config_path = Path(args.behavior_config).expanduser()
        if not behaviour_config_path.is_file():
            parser.error(f"Behaviour config not found: {behaviour_config_path}")

    behaviour_settings = load_behaviour_settings(behaviour_config_path)
    set_behaviour_settings(behaviour_settings)

    profile_name: str | None = None
    profile_name_path: Path | None = None
    if getattr(args, "profile_name", None):
        if args.command != "login":
            parser.error("--profile-name is only valid for the login command")
        try:
            profile_name = validate_profile_name(args.profile_name)
        except ValueError as exc:
            parser.error(str(exc))
        profile_name_path = _profile_alias_to_path(profile_name, profiles_root=profiles_root)
        if profile_name_path.exists():
            if args.fresh_profile:
                parser.error(
                    f"Chrome profile '{profile_name}' already exists under {profile_name_path}. Use a new name or remove the existing folder."
                )
            parser.error(
                f"Chrome profile '{profile_name}' already exists. Use --chrome-profile {profile_name} to reuse it."
            )
        args.profile_name = profile_name

    if args.command not in {"login", "session"} and not args.chrome_profile:
        parser.error("--chrome-profile <saved-name> is required for this command. Run the login command first to create one.")

    if args.chrome_profile and args.fresh_profile:
        parser.error("--fresh-profile cannot be combined with --chrome-profile")

    chrome_profile_alias: str | None = None
    chrome_profile_path: Path | None = None
    if args.chrome_profile:
        try:
            chrome_profile_alias = validate_profile_name(args.chrome_profile)
        except ValueError as exc:
            parser.error(str(exc))
        chrome_profile_path = _profile_alias_to_path(chrome_profile_alias, profiles_root=profiles_root)
        if not chrome_profile_path.exists():
            parser.error(
                f"Chrome profile '{chrome_profile_alias}' not found under {profiles_root}. Run the login command to create it."
            )
        args.chrome_profile = chrome_profile_alias

    if args.manual_timeout is not None and args.manual_timeout < 0:
        manual_timeout = None
    else:
        manual_timeout = args.manual_timeout

    user_data_dir = chrome_profile_path
    bootstrap_profile = args.fresh_profile
    if args.command == "login" and profile_name and args.fresh_profile:
        assert profile_name_path is not None
        profile_name_path.parent.mkdir(parents=True, exist_ok=True)
        user_data_dir = profile_name_path
        bootstrap_profile = False
    use_ephemeral_profile = user_data_dir is None and not args.fresh_profile
    driver_config = DriverConfig(
        headless=args.headless,
        user_data_dir=user_data_dir,
        use_ephemeral_profile=use_ephemeral_profile,
        bootstrap_profile=bootstrap_profile,
        profile_root=profiles_root,
        user_agent=args.user_agent,
    )
    bot = BotController(driver_config=driver_config)

    bot.start()

    if bot.profile_path and (args.fresh_profile or args.chrome_profile):
        label = "Fresh Chrome profile" if args.fresh_profile and not args.chrome_profile else "Chrome profile"
        print(f"{label}: {bot.profile_path}")

    try:
        if args.command == "login":
            final_state = bot.manual_login(
                manual_timeout=manual_timeout,
                persist_profile=True,
                profile_name=profile_name,
            )
            if final_state != bot.context.current_state:
                bot.context.update_state(final_state)
            print(f"Manual login completed with state: {final_state.name}")
            return 0

        if args.command == "session":
            _run_session(bot, default_manual_timeout=manual_timeout)
            return 0

        try:
            _execute_workflow(bot, args.command, args)
            return 0
        except ValueError as exc:
            parser.error(str(exc))
    finally:
        bot.stop()

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    sys.exit(main())

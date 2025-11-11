"""CLI entrypoint for the restructured weBot automation framework."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from weBot.bot import BotController
from weBot.brains.engage import process_feed
from weBot.config.settings import load_credentials
from weBot.data.graph_io import export_edges_to_csv
from weBot.data.storage import save_json
from weBot.workflows import follower_graph as follower_workflow
from weBot.workflows.profile import fetch_profile


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Automation toolkit for Twitter/X interactions")
    parser.add_argument("command", choices=["login", "engage", "follower-graph", "profile"], help="Task to run")
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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in {"follower-graph", "profile"} and not args.handle:
        parser.error("--handle is required for follower-graph and profile commands")

    credentials = load_credentials(Path(args.env_file) if args.env_file else None)

    from weBot.core.driver import DriverConfig

    driver_config = DriverConfig(headless=args.headless)
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

    try:
        prefer_cookies = not args.no_cookies
        final_state = bot.login(prefer_cookies=prefer_cookies)
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

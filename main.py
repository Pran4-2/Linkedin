"""
main.py – Entry point for the LinkedIn Easy Apply automation agent.

Usage:
    python main.py [--config config.yaml] [--summary]

Options:
    --config PATH   Path to the YAML configuration file. Default: config.yaml
    --summary       Print weekly summary and exit (does not launch the browser).
    --dry-run       Log in, search, but do not submit any applications.
"""

from __future__ import annotations

import argparse
import sys

import yaml

from logger import get_logger, print_weekly_summary
from linkedin_bot import LinkedInBot


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="LinkedIn Easy Apply automation agent."
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config.yaml (default: config.yaml)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print weekly application summary and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log in and search but do NOT submit any applications.",
    )
    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"ERROR: Config file '{args.config}' not found.")
        print("Please copy config.yaml and fill in your details.")
        return 1
    except yaml.YAMLError as exc:
        print(f"ERROR: Could not parse config file: {exc}")
        return 1

    # Set up logging
    log_cfg = config.get("logging", {})
    logger = get_logger(log_cfg.get("log_file", "bot.log"))

    # Weekly summary only
    if args.summary:
        print_weekly_summary(log_cfg.get("csv_path", "Applications.csv"))
        return 0

    # Safety guard: warn if credentials are placeholders
    linkedin_cfg = config.get("linkedin", {})
    if linkedin_cfg.get("email", "").startswith("your_"):
        logger.error(
            "LinkedIn credentials are not set. "
            "Please update config.yaml with your real email and password."
        )
        return 1

    # Dry-run mode: override max_applications to 0
    if args.dry_run:
        config.setdefault("search", {})["max_applications"] = 0
        logger.info("Dry-run mode: browser will open but no applications will be submitted.")

    # Run the bot
    bot = LinkedInBot(config)
    try:
        bot.start()
        bot.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user.")
    except Exception as exc:
        logger.exception("Unhandled error: %s", exc)
        return 1
    finally:
        bot.quit()
        applied = bot.applications_this_session
        logger.info("Session complete. Applications submitted this session: %d", applied)

        # Print summary at the end of each session
        print_weekly_summary(log_cfg.get("csv_path", "Applications.csv"))

    return 0


if __name__ == "__main__":
    sys.exit(main())

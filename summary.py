"""
summary.py – Standalone CLI to print weekly application summaries.

Usage:
    python summary.py
    python summary.py --csv Applications.csv
"""

import argparse

from logger import print_weekly_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Print weekly LinkedIn application summary.")
    parser.add_argument(
        "--csv",
        default="Applications.csv",
        help="Path to the Applications CSV file (default: Applications.csv)",
    )
    args = parser.parse_args()
    print_weekly_summary(args.csv)


if __name__ == "__main__":
    main()

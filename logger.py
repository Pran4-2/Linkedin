"""
logger.py – Application CSV logger and weekly summary helper.
"""

import csv
import logging
import os
from datetime import datetime, timedelta

FIELDNAMES = [
    "Job Title",
    "Company",
    "Date Applied",
    "Method",
    "Status",
    "Follow-up",
    "Notes",
]

# Cache of CSV paths already initialised in this process to avoid repeated
# filesystem checks when logging many applications in a single session.
_initialised_csvs: set[str] = set()


def get_logger(log_file: str = "bot.log") -> logging.Logger:
    """Return a configured root logger that writes to both console and a file."""
    logger = logging.getLogger("linkedin_bot")
    if logger.handlers:
        return logger  # already configured

    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    # File handler
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


def ensure_csv(csv_path: str) -> None:
    """Create the CSV with headers if it does not already exist."""
    if csv_path in _initialised_csvs:
        return
    if not os.path.exists(csv_path):
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
    _initialised_csvs.add(csv_path)


def log_application(
    csv_path: str,
    job_title: str,
    company: str,
    method: str = "LinkedIn Easy Apply",
    status: str = "Applied",
    follow_up: str = "",
    notes: str = "",
) -> None:
    """Append a single application record to the CSV log."""
    ensure_csv(csv_path)
    row = {
        "Job Title": job_title,
        "Company": company,
        "Date Applied": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "Method": method,
        "Status": status,
        "Follow-up": follow_up,
        "Notes": notes,
    }
    with open(csv_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(row)


def weekly_summary(csv_path: str) -> dict:
    """
    Read Applications.csv and return a summary dict for the past 7 days.

    Returns:
        {
            "period":           "YYYY-MM-DD to YYYY-MM-DD",
            "total_applied":    int,
            "total_responses":  int,   # status contains 'response'/'interview'/'offer'
            "response_rate":    str,   # "0.0 %"
            "follow_ups_due":   int,
            "by_status":        dict,
        }
    """
    ensure_csv(csv_path)
    cutoff = datetime.now() - timedelta(days=7)

    total = 0
    responses = 0
    follow_ups = 0
    by_status: dict[str, int] = {}

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                applied_dt = datetime.strptime(row["Date Applied"], "%Y-%m-%d %H:%M")
            except (ValueError, KeyError):
                continue
            if applied_dt < cutoff:
                continue

            total += 1
            status = row.get("Status", "").lower()
            by_status[status] = by_status.get(status, 0) + 1

            if any(kw in status for kw in ("response", "interview", "offer", "screen")):
                responses += 1

            if row.get("Follow-up", "").strip().upper() == "YES":
                follow_ups += 1

    rate = f"{(responses / total * 100):.1f} %" if total else "0.0 %"
    period_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    period_end = datetime.now().strftime("%Y-%m-%d")

    return {
        "period": f"{period_start} to {period_end}",
        "total_applied": total,
        "total_responses": responses,
        "response_rate": rate,
        "follow_ups_due": follow_ups,
        "by_status": by_status,
    }


def print_weekly_summary(csv_path: str) -> None:
    """Print a formatted weekly summary to stdout."""
    s = weekly_summary(csv_path)
    print("\n" + "=" * 50)
    print("       WEEKLY APPLICATION SUMMARY")
    print("=" * 50)
    print(f"  Period        : {s['period']}")
    print(f"  Total Applied : {s['total_applied']}")
    print(f"  Responses     : {s['total_responses']}")
    print(f"  Response Rate : {s['response_rate']}")
    print(f"  Follow-ups    : {s['follow_ups_due']}")
    if s["by_status"]:
        print("\n  Breakdown by Status:")
        for status, count in sorted(s["by_status"].items()):
            print(f"    {status:<25} {count}")
    print("=" * 50 + "\n")

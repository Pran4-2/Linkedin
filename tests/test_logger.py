"""
tests/test_logger.py – Unit tests for CSV logging and weekly summary.
"""

import csv
import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from logger import ensure_csv, log_application, weekly_summary, FIELDNAMES


@pytest.fixture
def tmp_csv(tmp_path):
    return str(tmp_path / "test_applications.csv")


def test_ensure_csv_creates_file(tmp_csv):
    ensure_csv(tmp_csv)
    assert os.path.exists(tmp_csv)
    with open(tmp_csv, newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == FIELDNAMES


def test_ensure_csv_idempotent(tmp_csv):
    ensure_csv(tmp_csv)
    ensure_csv(tmp_csv)  # Should not raise or overwrite
    with open(tmp_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows == []


def test_log_application_writes_row(tmp_csv):
    log_application(tmp_csv, "SOC Analyst", "Acme Corp")
    with open(tmp_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["Job Title"] == "SOC Analyst"
    assert rows[0]["Company"] == "Acme Corp"
    assert rows[0]["Status"] == "Applied"
    assert rows[0]["Method"] == "LinkedIn Easy Apply"


def test_log_application_multiple_rows(tmp_csv):
    log_application(tmp_csv, "SOC Analyst", "Acme Corp")
    log_application(tmp_csv, "Incident Responder", "Beta Ltd", status="Failed")
    with open(tmp_csv, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[1]["Status"] == "Failed"


def test_weekly_summary_counts(tmp_csv):
    log_application(tmp_csv, "SOC Analyst", "Acme Corp", status="Applied")
    log_application(tmp_csv, "IR Analyst", "Beta Ltd", status="Interview")
    log_application(tmp_csv, "Security Eng", "Gamma", status="Applied")

    summary = weekly_summary(tmp_csv)
    assert summary["total_applied"] == 3
    assert summary["total_responses"] == 1  # only "Interview" matches response keywords
    assert summary["response_rate"] != "0.0 %"


def test_weekly_summary_empty(tmp_csv):
    summary = weekly_summary(tmp_csv)
    assert summary["total_applied"] == 0
    assert summary["response_rate"] == "0.0 %"


def test_weekly_summary_excludes_old_entries(tmp_csv):
    # Manually write an entry older than 7 days
    ensure_csv(tmp_csv)
    old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
    with open(tmp_csv, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow({
            "Job Title": "Old Job",
            "Company": "Old Corp",
            "Date Applied": old_date,
            "Method": "LinkedIn Easy Apply",
            "Status": "Applied",
            "Follow-up": "",
            "Notes": "",
        })

    log_application(tmp_csv, "New Job", "New Corp")
    summary = weekly_summary(tmp_csv)
    assert summary["total_applied"] == 1  # Only the recent one

"""
tests/test_question_answerer.py – Unit tests for QuestionAnswerer.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from question_answerer import QuestionAnswerer

SAMPLE_CONFIG = {
    "personal": {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "phone": "+91 9999999999",
        "city": "Bangalore",
        "country": "India",
        "linkedin_profile": "https://linkedin.com/in/johndoe",
    },
    "background": {
        "years_of_experience": 3,
        "highest_education": "Bachelor's Degree",
        "notice_period_days": 30,
        "expected_salary": 800000,
        "currency": "INR",
    },
    "eligibility": {
        "legally_authorized": True,
        "require_sponsorship": False,
    },
    "answers": {
        "yes_no": {
            "authorized to work": True,
            "require sponsorship": False,
            "willing to relocate": True,
        },
        "numeric": {
            "years of experience": 3,
            "notice period": 30,
        },
        "star_answers": {
            "tell me about yourself": "I am a cybersecurity professional.",
        },
    },
}


@pytest.fixture
def qa():
    return QuestionAnswerer(SAMPLE_CONFIG)


def test_boolean_yes(qa):
    assert qa.answer("Are you authorized to work in India?", "boolean") == "Yes"


def test_boolean_no(qa):
    assert qa.answer("Will you require sponsorship?", "boolean") == "No"


def test_numeric_experience(qa):
    result = qa.answer("How many years of experience do you have?", "numeric")
    assert result == "3"


def test_numeric_notice(qa):
    result = qa.answer("What is your notice period in days?", "numeric")
    assert result == "30"


def test_free_text_first_name(qa):
    assert qa.answer("first name") == "John"


def test_free_text_last_name(qa):
    assert qa.answer("last name") == "Doe"


def test_free_text_email(qa):
    assert qa.answer("email address") == "john@example.com"


def test_free_text_city(qa):
    assert qa.answer("city") == "Bangalore"


def test_free_text_salary(qa):
    result = qa.answer("What is your expected salary?")
    assert result == "800000"


def test_free_text_star(qa):
    result = qa.answer("tell me about yourself")
    assert "cybersecurity" in result.lower()


def test_dropdown_best_option_yes_no(qa):
    opts = ["Yes", "No"]
    result = qa.best_dropdown_option("Are you willing to relocate?", opts)
    assert result == "Yes"


def test_dropdown_best_option_country(qa):
    opts = ["United States", "India", "United Kingdom"]
    result = qa.best_dropdown_option("Country of residence", opts)
    assert result == "India"


def test_dropdown_best_option_currency(qa):
    opts = ["USD", "EUR", "INR", "GBP"]
    result = qa.best_dropdown_option("Preferred currency", opts)
    assert result == "INR"


def test_dropdown_fallback_to_first(qa):
    opts = ["Option A", "Option B"]
    result = qa.best_dropdown_option("Unknown question", opts)
    assert result == "Option A"


def test_clean_label():
    assert QuestionAnswerer.clean_label("  First Name *  ") == "First Name"
    assert QuestionAnswerer.clean_label("Are you eligible? *") == "Are you eligible?"

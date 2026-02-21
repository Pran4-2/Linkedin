"""
tests/test_form_filler.py – Unit tests for FormFiller navigation methods.
"""

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from selenium.common.exceptions import NoSuchElementException

from form_filler import FormFiller


MINIMAL_CONFIG = {
    "browser": {"implicitly_wait": 1},
    "personal": {"first_name": "Test"},
    "documents": {},
    "answers": {"yes_no": {}, "numeric": {}, "star_answers": {}},
}


@pytest.fixture
def filler():
    driver = MagicMock()
    f = FormFiller(driver, MINIMAL_CONFIG)
    return f


class TestTryNext:
    """Ensure _try_next only looks for Next and Continue, not Review."""

    def test_clicks_next_button(self, filler):
        btn = MagicMock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        filler.driver.find_element.return_value = btn

        result = filler._try_next()
        assert result is True
        btn.click.assert_called_once()

    def test_returns_false_when_no_button(self, filler):
        filler.driver.find_element.side_effect = NoSuchElementException()

        result = filler._try_next()
        assert result is False

    def test_does_not_match_review(self, filler):
        """_try_next should NOT match Review buttons; _try_review handles those."""
        calls = []

        def mock_find(by, xpath):
            calls.append(xpath)
            raise NoSuchElementException()

        filler.driver.find_element.side_effect = mock_find
        filler._try_next()

        # Verify "Review" is not in any of the XPath selectors tried
        for xpath in calls:
            assert "Review" not in xpath


class TestTryReview:
    """Ensure _try_review handles Review buttons."""

    def test_clicks_review_button(self, filler):
        btn = MagicMock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        filler.driver.find_element.return_value = btn

        result = filler._try_review()
        assert result is True
        btn.click.assert_called_once()

    def test_returns_false_when_no_review(self, filler):
        filler.driver.find_element.side_effect = NoSuchElementException()

        result = filler._try_review()
        assert result is False


class TestTrySubmit:
    """Ensure _try_submit handles Submit buttons."""

    def test_clicks_submit_button(self, filler):
        btn = MagicMock()
        btn.is_displayed.return_value = True
        btn.is_enabled.return_value = True
        filler.driver.find_element.return_value = btn

        result = filler._try_submit()
        assert result is True
        btn.click.assert_called_once()

    def test_returns_false_when_no_submit(self, filler):
        filler.driver.find_element.side_effect = NoSuchElementException()

        result = filler._try_submit()
        assert result is False

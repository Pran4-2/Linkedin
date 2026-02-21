"""
tests/test_linkedin_bot.py – Unit tests for LinkedInBot Easy Apply flow.

Uses mock objects to simulate Selenium WebDriver interactions.
"""

import os
import sys
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
)

from linkedin_bot import LinkedInBot


MINIMAL_CONFIG = {
    "linkedin": {"email": "test@example.com", "password": "pass"},
    "search": {"job_titles": ["Analyst"], "locations": ["Bangalore"], "max_applications": 50},
    "browser": {"implicitly_wait": 1},
    "logging": {"csv_path": "/tmp/test_app.csv"},
    "personal": {"first_name": "Test"},
    "documents": {},
    "answers": {"yes_no": {}, "numeric": {}, "star_answers": {}},
}


@pytest.fixture
def bot():
    b = LinkedInBot(MINIMAL_CONFIG)
    b.driver = MagicMock()
    b.wait = MagicMock()
    return b


class TestFindEasyApplyButton:
    """Tests for _find_easy_apply_button using WebDriverWait."""

    @patch("linkedin_bot.WebDriverWait")
    def test_returns_button_when_found(self, mock_wdw, bot):
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True
        mock_wdw.return_value.until.return_value = mock_btn

        result = bot._find_easy_apply_button()
        assert result is mock_btn

    @patch("linkedin_bot.WebDriverWait")
    def test_returns_none_when_no_button(self, mock_wdw, bot):
        mock_wdw.return_value.until.side_effect = TimeoutException()

        result = bot._find_easy_apply_button()
        assert result is None

    @patch("linkedin_bot.WebDriverWait")
    def test_returns_none_when_button_not_displayed(self, mock_wdw, bot):
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = False
        mock_wdw.return_value.until.return_value = mock_btn

        result = bot._find_easy_apply_button()
        # All three selectors return non-displayed buttons → None
        assert result is None

    @patch("linkedin_bot.WebDriverWait")
    def test_tries_multiple_selectors(self, mock_wdw, bot):
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True

        # First two selectors fail, third succeeds
        mock_wdw.return_value.until.side_effect = [
            TimeoutException(),
            TimeoutException(),
            mock_btn,
        ]

        result = bot._find_easy_apply_button()
        assert result is mock_btn
        assert mock_wdw.return_value.until.call_count == 3


class TestApplyToJob:
    """Tests for _apply_to_job: detail pane wait, button click, modal wait."""

    @patch("linkedin_bot.FormFiller")
    def test_successful_application(self, mock_filler_cls, bot, tmp_path):
        bot.csv_path = str(tmp_path / "apps.csv")

        card = MagicMock()
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True

        # Wait for detail pane succeeds
        bot.wait.until.return_value = MagicMock()

        # _find_easy_apply_button returns a button
        with patch.object(bot, "_find_easy_apply_button", return_value=mock_btn):
            # FormFiller.fill_application returns True
            mock_filler_cls.return_value.fill_application.return_value = True
            result = bot._apply_to_job(card, "SOC Analyst", "Acme Corp")

        assert result is True
        assert bot.applications_this_session == 1
        # Easy Apply button should be scrolled into view and clicked
        bot.driver.execute_script.assert_called_once()
        mock_btn.click.assert_called_once()

    @patch("linkedin_bot.FormFiller")
    def test_no_easy_apply_button_returns_false(self, mock_filler_cls, bot):
        card = MagicMock()
        bot.wait.until.return_value = MagicMock()

        with patch.object(bot, "_find_easy_apply_button", return_value=None):
            result = bot._apply_to_job(card, "SOC Analyst", "Acme Corp")

        assert result is False
        assert bot.applications_this_session == 0
        mock_filler_cls.assert_not_called()

    def test_detail_pane_timeout_returns_false(self, bot):
        card = MagicMock()
        bot.wait.until.side_effect = TimeoutException()

        result = bot._apply_to_job(card, "SOC Analyst", "Acme Corp")
        assert result is False
        assert bot.applications_this_session == 0

    @patch("linkedin_bot.FormFiller")
    def test_modal_timeout_returns_false(self, mock_filler_cls, bot):
        card = MagicMock()
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True

        # First wait (detail pane) succeeds, second wait (modal) times out
        bot.wait.until.side_effect = [MagicMock(), TimeoutException()]

        with patch.object(bot, "_find_easy_apply_button", return_value=mock_btn):
            result = bot._apply_to_job(card, "SOC Analyst", "Acme Corp")

        assert result is False
        mock_filler_cls.assert_not_called()

    @patch("linkedin_bot.FormFiller")
    def test_form_fill_failure_returns_false(self, mock_filler_cls, bot, tmp_path):
        bot.csv_path = str(tmp_path / "apps.csv")
        card = MagicMock()
        mock_btn = MagicMock()
        mock_btn.is_displayed.return_value = True

        bot.wait.until.return_value = MagicMock()

        with patch.object(bot, "_find_easy_apply_button", return_value=mock_btn):
            mock_filler_cls.return_value.fill_application.return_value = False
            with patch.object(bot, "_close_modal"):
                result = bot._apply_to_job(card, "SOC Analyst", "Acme Corp")

        assert result is False
        assert bot.applications_this_session == 0


class TestBuildSearchUrl:
    """Tests for _build_search_url."""

    def test_includes_easy_apply_filter(self, bot):
        url = bot._build_search_url("SOC Analyst", "Bangalore")
        assert "f_LF=f_AL" in url

    def test_includes_keywords(self, bot):
        url = bot._build_search_url("SOC Analyst", "Bangalore")
        assert "keywords=SOC+Analyst" in url or "keywords=SOC%20Analyst" in url

    def test_includes_location(self, bot):
        url = bot._build_search_url("SOC Analyst", "Bangalore")
        assert "location=Bangalore" in url

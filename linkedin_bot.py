"""
linkedin_bot.py – Core Selenium automation for LinkedIn Easy Apply.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Generator

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from form_filler import FormFiller
from logger import log_application

logger = logging.getLogger("linkedin_bot")

LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"

# Experience level → LinkedIn filter value
EXP_LEVEL_MAP = {
    "internship": "1",
    "entry level": "2",
    "associate": "3",
    "mid-senior level": "4",
    "director": "5",
    "executive": "6",
}

DATE_POSTED_MAP = {
    "past_24_hours": "r86400",
    "past_week": "r604800",
    "past_month": "r2592000",
    "any_time": "",
}


class LinkedInBot:
    """Automates searching and applying to LinkedIn Easy Apply jobs."""

    def __init__(self, config: dict) -> None:
        self.config = config
        self.browser_cfg = config.get("browser", {})
        self.search_cfg = config.get("search", {})
        self.linkedin_cfg = config.get("linkedin", {})
        self.log_cfg = config.get("logging", {})
        self.csv_path = self.log_cfg.get("csv_path", "Applications.csv")
        self.driver: webdriver.Chrome | None = None
        self.wait: WebDriverWait | None = None
        self.applications_this_session = 0
        self.max_applications = self.search_cfg.get("max_applications", 50)

    # ── Browser lifecycle ─────────────────────────────────────────────────────

    def start(self) -> None:
        """Launch Chrome and log in to LinkedIn."""
        options = ChromeOptions()
        if self.browser_cfg.get("headless", False):
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        options.add_argument("--start-maximized")

        service = ChromeService(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.wait = WebDriverWait(
            self.driver,
            self.browser_cfg.get("implicitly_wait", 10),
        )
        logger.info("Browser started.")
        self._login()

    def quit(self) -> None:
        if self.driver:
            self.driver.quit()
            logger.info("Browser closed.")

    # ── Authentication ────────────────────────────────────────────────────────

    def _login(self) -> None:
        self.driver.get(LINKEDIN_LOGIN_URL)
        time.sleep(2)
        try:
            email_input = self.wait.until(EC.presence_of_element_located((By.ID, "username")))
            email_input.send_keys(self.linkedin_cfg.get("email", ""))
            self.driver.find_element(By.ID, "password").send_keys(
                self.linkedin_cfg.get("password", "")
            )
            self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
            time.sleep(3)
            logger.info("Logged in to LinkedIn.")
        except TimeoutException:
            logger.error("Login page did not load correctly.")
            raise

    # ── Job search ────────────────────────────────────────────────────────────

    def run(self) -> None:
        """Main loop: iterate over job titles and apply."""
        job_titles = self.search_cfg.get("job_titles", [])
        locations = self.search_cfg.get("locations", ["Bangalore"])

        for title in job_titles:
            for location in locations:
                if self.applications_this_session >= self.max_applications:
                    logger.info("Reached max applications limit (%d).", self.max_applications)
                    return
                logger.info("Searching: '%s' in '%s'", title, location)
                self._search_and_apply(title, location)

    def _search_and_apply(self, job_title: str, location: str) -> None:
        """Search for a job title in a location and apply to Easy Apply listings."""
        url = self._build_search_url(job_title, location)
        self.driver.get(url)
        time.sleep(3)

        page = 1
        while self.applications_this_session < self.max_applications:
            logger.info("Processing search results page %d", page)
            applied_on_page = 0

            for job_card in self._iter_job_cards():
                if self.applications_this_session >= self.max_applications:
                    break
                title_text, company_text = self._extract_card_info(job_card)
                if not title_text:
                    continue

                logger.info("Attempting: %s @ %s", title_text, company_text)
                if self._apply_to_job(job_card, title_text, company_text):
                    applied_on_page += 1

            # Try to navigate to next page
            if not self._go_to_next_page():
                logger.info("No more pages for '%s' in '%s'.", job_title, location)
                break
            page += 1
            time.sleep(2)

    def _iter_job_cards(self) -> Generator:
        """Yield job card elements from the current results list."""
        try:
            cards = self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, ".jobs-search__results-list li, .scaffold-layout__list-item")
                )
            )
            for card in cards:
                yield card
        except TimeoutException:
            logger.warning("No job cards found on the page.")

    def _extract_card_info(self, card) -> tuple[str, str]:
        """Return (job_title, company) from a job card element."""
        try:
            title = card.find_element(By.CSS_SELECTOR, "h3, .job-card-list__title, .base-search-card__title").text.strip()
        except NoSuchElementException:
            title = ""
        try:
            company = card.find_element(By.CSS_SELECTOR, "h4, .job-card-container__company-name, .base-search-card__subtitle").text.strip()
        except NoSuchElementException:
            company = ""
        return title, company

    def _apply_to_job(self, card: object, title: str, company: str) -> bool:
        """
        Click a job card, open Easy Apply, fill the form, and submit.
        Returns True if successfully applied.
        """
        try:
            # Click the card to load job details
            try:
                card.find_element(By.CSS_SELECTOR, "a, .job-card-list__title").click()
            except NoSuchElementException:
                card.click()

            # Wait for the job detail pane to load
            try:
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, ".jobs-details, .job-view-layout, .jobs-unified-top-card")
                    )
                )
            except TimeoutException:
                logger.info("Job detail pane did not load for: %s @ %s", title, company)
                return False

            # Look for Easy Apply button in the job detail pane
            easy_apply_btn = self._find_easy_apply_button()
            if not easy_apply_btn:
                logger.info("No Easy Apply button for: %s @ %s", title, company)
                return False

            # Scroll to and click the Easy Apply button
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block: 'center'});", easy_apply_btn
            )
            WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(easy_apply_btn)
            )
            easy_apply_btn.click()

            # Wait for the Easy Apply modal to appear
            try:
                self.wait.until(
                    EC.presence_of_element_located(
                        (By.CLASS_NAME, "jobs-easy-apply-modal")
                    )
                )
            except TimeoutException:
                logger.info("Easy Apply modal did not open for: %s @ %s", title, company)
                return False

            # Fill the form
            filler = FormFiller(self.driver, self.config)
            success = filler.fill_application()

            if success:
                self.applications_this_session += 1
                log_application(
                    self.csv_path,
                    job_title=title,
                    company=company,
                    status="Applied",
                )
                logger.info(
                    "[%d] Applied: %s @ %s",
                    self.applications_this_session,
                    title,
                    company,
                )
                return True
            else:
                self._close_modal()
                log_application(
                    self.csv_path,
                    job_title=title,
                    company=company,
                    status="Failed",
                    notes="Could not complete form",
                )
                return False

        except (StaleElementReferenceException, TimeoutException, Exception) as exc:
            logger.warning("Error applying to %s @ %s: %s", title, company, exc)
            self._close_modal()
            return False

    def _find_easy_apply_button(self):
        """Return the Easy Apply button element if present, else None."""
        selectors = [
            "//button[contains(@class,'jobs-apply-button') and contains(.,'Easy Apply')]",
            "//button[contains(@class,'jobs-apply-button')]",
            "//button[contains(.,'Easy Apply')]",
        ]
        for xpath in selectors:
            try:
                btn = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                if btn.is_displayed():
                    return btn
            except (TimeoutException, NoSuchElementException):
                continue
        return None

    def _close_modal(self) -> None:
        """Dismiss an open Easy Apply modal without submitting."""
        for selector in [
            "button[aria-label='Dismiss']",
            "button[data-control-name='discard_application_confirm_btn']",
        ]:
            try:
                btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                btn.click()
                time.sleep(1)
                return
            except NoSuchElementException:
                continue
        # Fallback: click discard if confirmation dialog appeared
        try:
            self.driver.find_element(By.XPATH, "//button[contains(.,'Discard')]").click()
        except NoSuchElementException:
            pass

    def _go_to_next_page(self) -> bool:
        """Click the 'Next' pagination button. Returns False if not found."""
        try:
            next_btn = self.driver.find_element(
                By.XPATH,
                "//button[@aria-label='Next'] | //button[contains(@aria-label,'next page')]",
            )
            if next_btn.is_enabled():
                next_btn.click()
                return True
        except NoSuchElementException:
            pass
        return False

    # ── URL builder ───────────────────────────────────────────────────────────

    def _build_search_url(self, job_title: str, location: str) -> str:
        """Construct a LinkedIn job search URL with filters."""
        import urllib.parse

        params = {
            "keywords": job_title,
            "location": location,
        }

        if self.search_cfg.get("easy_apply_only", True):
            params["f_LF"] = "f_AL"  # Easy Apply filter

        date_key = self.search_cfg.get("date_posted", "past_month")
        date_val = DATE_POSTED_MAP.get(date_key, "")
        if date_val:
            params["f_TPR"] = date_val

        exp_levels = self.search_cfg.get("experience_levels", [])
        if exp_levels:
            codes = [EXP_LEVEL_MAP[e.lower()] for e in exp_levels if e.lower() in EXP_LEVEL_MAP]
            if codes:
                params["f_E"] = ",".join(codes)

        return LINKEDIN_JOBS_URL + "?" + urllib.parse.urlencode(params)

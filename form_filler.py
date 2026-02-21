"""
form_filler.py – Handles filling in LinkedIn Easy Apply multi-step forms.
"""

from __future__ import annotations

import logging
import os
import time

from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from question_answerer import QuestionAnswerer

logger = logging.getLogger("linkedin_bot")


class FormFiller:
    """Fills out an open Easy Apply modal form step by step."""

    def __init__(self, driver: WebDriver, config: dict) -> None:
        self.driver = driver
        self.config = config
        self.wait = WebDriverWait(driver, config.get("browser", {}).get("implicitly_wait", 10))
        self.qa = QuestionAnswerer(config)
        self.docs = config.get("documents", {})
        self.personal = config.get("personal", {})

    # ── Entry point ───────────────────────────────────────────────────────────

    def fill_application(self) -> bool:
        """
        Drive the full Easy Apply multi-step form.
        Returns True when the application is submitted, False on failure.
        """
        max_steps = 15  # guard against infinite loops
        for step in range(max_steps):
            logger.debug("Easy Apply step %d", step + 1)
            time.sleep(1)

            # Fill visible fields on current page
            self._fill_current_page()

            # Decide next action
            if self._try_submit():
                logger.info("Application submitted.")
                return True
            if self._try_next():
                continue
            if self._try_review():
                continue

            # If none of the above worked, we may be stuck
            logger.warning("Could not advance the form on step %d.", step + 1)
            break

        return False

    # ── Page-level filling ────────────────────────────────────────────────────

    def _fill_current_page(self) -> None:
        """Fill all visible form fields on the current modal page."""
        try:
            modal = self.wait.until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-easy-apply-modal"))
            )
        except TimeoutException:
            logger.warning("Easy Apply modal not found.")
            return

        self._fill_text_inputs(modal)
        self._fill_selects(modal)
        self._fill_radios(modal)
        self._fill_checkboxes(modal)
        self._fill_textareas(modal)
        self._handle_file_uploads(modal)

    def _fill_text_inputs(self, modal: WebElement) -> None:
        inputs = modal.find_elements(By.CSS_SELECTOR, "input[type='text'], input[type='email'], input[type='tel'], input[type='number']")
        for inp in inputs:
            try:
                if not inp.is_displayed() or not inp.is_enabled():
                    continue
                current_val = inp.get_attribute("value") or ""
                if current_val.strip():
                    continue  # already filled

                label_text = self._get_label_for(inp, modal)
                answer = self.qa.answer(label_text, field_type="text")
                if answer:
                    inp.clear()
                    inp.send_keys(answer)
                    logger.debug("Filled text input [%s] = %s", label_text, answer)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue

    def _fill_selects(self, modal: WebElement) -> None:
        selects = modal.find_elements(By.TAG_NAME, "select")
        for sel in selects:
            try:
                if not sel.is_displayed() or not sel.is_enabled():
                    continue
                label_text = self._get_label_for(sel, modal)
                select_obj = Select(sel)
                options = [o.text for o in select_obj.options if o.text.strip() and o.get_attribute("value") not in ("", "Select an option")]
                if not options:
                    continue
                best = self.qa.best_dropdown_option(label_text, options)
                select_obj.select_by_visible_text(best)
                logger.debug("Selected [%s] = %s", label_text, best)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue

    def _fill_radios(self, modal: WebElement) -> None:
        """For radio groups, pick Yes/True options by default where relevant."""
        groups: dict[str, list[WebElement]] = {}
        radios = modal.find_elements(By.CSS_SELECTOR, "input[type='radio']")
        for radio in radios:
            try:
                name = radio.get_attribute("name") or ""
                groups.setdefault(name, []).append(radio)
            except StaleElementReferenceException:
                continue

        for name, radio_list in groups.items():
            # Skip if already selected
            if any(r.is_selected() for r in radio_list):
                continue
            label_text = self._get_label_for(radio_list[0], modal)
            # Determine desired answer
            answer = self.qa.answer(label_text, field_type="boolean")
            for radio in radio_list:
                try:
                    sib_label = radio.find_element(By.XPATH, "following-sibling::label").text.strip()
                except NoSuchElementException:
                    sib_label = ""
                if answer.lower() in sib_label.lower() or sib_label.lower() in answer.lower():
                    try:
                        radio.click()
                        logger.debug("Clicked radio [%s] = %s", label_text, sib_label)
                        break
                    except ElementNotInteractableException:
                        continue

    def _fill_checkboxes(self, modal: WebElement) -> None:
        checkboxes = modal.find_elements(By.CSS_SELECTOR, "input[type='checkbox']")
        for cb in checkboxes:
            try:
                if not cb.is_displayed():
                    continue
                label_text = self._get_label_for(cb, modal).lower()
                # Only check mandatory consent / acknowledgement checkboxes
                if any(kw in label_text for kw in ("agree", "consent", "acknowledge", "confirm")):
                    if not cb.is_selected():
                        cb.click()
                        logger.debug("Checked checkbox: %s", label_text)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue

    def _fill_textareas(self, modal: WebElement) -> None:
        textareas = modal.find_elements(By.TAG_NAME, "textarea")
        for ta in textareas:
            try:
                if not ta.is_displayed() or not ta.is_enabled():
                    continue
                if (ta.get_attribute("value") or "").strip():
                    continue
                label_text = self._get_label_for(ta, modal)
                answer = self.qa.answer(label_text, field_type="text")
                if answer:
                    ta.clear()
                    ta.send_keys(answer)
                    logger.debug("Filled textarea [%s]", label_text)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue

    def _handle_file_uploads(self, modal: WebElement) -> None:
        file_inputs = modal.find_elements(By.CSS_SELECTOR, "input[type='file']")
        for fi in file_inputs:
            try:
                label_text = self._get_label_for(fi, modal).lower()
                if "cover" in label_text:
                    path = self.docs.get("cover_letter_path", "")
                else:
                    path = self.docs.get("cv_path", "")

                if path and os.path.isabs(path):
                    abs_path = path
                else:
                    abs_path = os.path.abspath(path) if path else ""

                if abs_path and os.path.exists(abs_path):
                    fi.send_keys(abs_path)
                    logger.info("Uploaded file [%s]: %s", label_text, abs_path)
                else:
                    logger.warning("File not found for upload [%s]: %s", label_text, abs_path)
            except (StaleElementReferenceException, ElementNotInteractableException):
                continue

    # ── Navigation helpers ────────────────────────────────────────────────────

    def _try_submit(self) -> bool:
        for text in ("Submit application", "Submit"):
            try:
                btn = self.driver.find_element(By.XPATH, f"//button[contains(., '{text}')]")
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(2)
                    return True
            except NoSuchElementException:
                continue
        return False

    def _try_next(self) -> bool:
        for text in ("Next", "Continue", "Review"):
            try:
                btn = self.driver.find_element(By.XPATH, f"//button[contains(., '{text}')]")
                if btn.is_displayed() and btn.is_enabled():
                    btn.click()
                    time.sleep(1)
                    return True
            except NoSuchElementException:
                continue
        return False

    def _try_review(self) -> bool:
        try:
            btn = self.driver.find_element(By.XPATH, "//button[contains(., 'Review')]")
            if btn.is_displayed() and btn.is_enabled():
                btn.click()
                time.sleep(1)
                return True
        except NoSuchElementException:
            pass
        return False

    # ── Label resolution ──────────────────────────────────────────────────────

    def _get_label_for(self, element: WebElement, modal: WebElement) -> str:
        """Try to find the label text associated with a form element."""
        # 1. aria-label attribute
        aria = element.get_attribute("aria-label") or ""
        if aria:
            return aria

        # 2. placeholder attribute
        placeholder = element.get_attribute("placeholder") or ""
        if placeholder:
            return placeholder

        # 3. Associated <label> via id
        el_id = element.get_attribute("id")
        if el_id:
            try:
                label = modal.find_element(By.CSS_SELECTOR, f"label[for='{el_id}']")
                return label.text.strip()
            except NoSuchElementException:
                pass

        # 4. Parent/ancestor label
        try:
            label = element.find_element(By.XPATH, "ancestor::label")
            return label.text.strip()
        except NoSuchElementException:
            pass

        # 5. Preceding sibling or nearby label
        try:
            label = element.find_element(By.XPATH, "preceding-sibling::label[1]")
            return label.text.strip()
        except NoSuchElementException:
            pass

        return ""

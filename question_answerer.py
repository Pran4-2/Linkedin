"""
question_answerer.py – Intelligently answers LinkedIn Easy Apply screening questions.

Strategy:
  1. Boolean / Yes-No  → look up config answer map.
  2. Numeric           → look up config numeric map.
  3. Dropdown          → pick the best matching option.
  4. Free-text         → return the most relevant STAR answer from config,
                         or a sensible generic fallback.
"""

from __future__ import annotations

import re


class QuestionAnswerer:
    """Answers screening questions based on config data."""

    def __init__(self, config: dict) -> None:
        self.personal = config.get("personal", {})
        self.background = config.get("background", {})
        self.eligibility = config.get("eligibility", {})
        self.answers_cfg = config.get("answers", {})
        self.yes_no_map: dict[str, bool] = {
            k.lower(): v
            for k, v in self.answers_cfg.get("yes_no", {}).items()
        }
        self.numeric_map: dict[str, float] = {
            k.lower(): v
            for k, v in self.answers_cfg.get("numeric", {}).items()
        }
        self.star_map: dict[str, str] = {
            k.lower(): v
            for k, v in self.answers_cfg.get("star_answers", {}).items()
        }

    # ── Public API ────────────────────────────────────────────────────────────

    def answer(self, question_text: str, field_type: str = "text") -> str:
        """
        Return the best string answer for a given question.

        Parameters
        ----------
        question_text : str  The full question text as shown on the form.
        field_type    : str  One of 'text', 'boolean', 'numeric', 'dropdown'.
        """
        q = question_text.lower().strip()

        if field_type == "boolean":
            return "Yes" if self._lookup_yes_no(q) else "No"

        if field_type == "numeric":
            return str(self._lookup_numeric(q))

        if field_type == "dropdown":
            # Caller should pass options separately; here we return a keyword
            return self._dropdown_hint(q)

        # Free-text / textarea
        return self._free_text_answer(q)

    def best_dropdown_option(self, question_text: str, options: list[str]) -> str:
        """
        Given a list of dropdown options, pick the best one.
        Returns the first option if nothing better is found.
        """
        if not options:
            return ""
        q = question_text.lower()

        # Yes/No dropdowns
        if self._is_yes_no_question(q):
            want = "Yes" if self._lookup_yes_no(q) else "No"
            for opt in options:
                if want.lower() in opt.lower():
                    return opt
            return options[0]

        # Education dropdowns
        if "education" in q or "degree" in q:
            target = self.background.get("highest_education", "").lower()
            for opt in options:
                if target and target in opt.lower():
                    return opt

        # Experience level dropdowns
        if "experience" in q:
            years = str(self.background.get("years_of_experience", 2))
            for opt in options:
                if years in opt:
                    return opt

        # Country/Location
        if "country" in q:
            country = self.personal.get("country", "India").lower()
            for opt in options:
                if country in opt.lower():
                    return opt

        # Currency
        if "currency" in q:
            currency = self.background.get("currency", "INR").lower()
            for opt in options:
                if currency in opt.lower():
                    return opt

        return options[0]

    # ── Private Helpers ───────────────────────────────────────────────────────

    def _is_yes_no_question(self, q: str) -> bool:
        """Heuristic: question is boolean if it starts with 'are/is/do/will/have/can'."""
        starters = ("are ", "is ", "do ", "will ", "have ", "can ", "were ", "did ")
        return any(q.startswith(s) for s in starters)

    def _lookup_yes_no(self, q: str) -> bool:
        """Return True/False from the config yes_no map, default True."""
        for key, val in self.yes_no_map.items():
            if key in q:
                return bool(val)
        # Safe defaults
        if "sponsorship" in q or "visa" in q:
            return bool(self.eligibility.get("require_sponsorship", False))
        if "authorized" in q or "eligible" in q:
            return bool(self.eligibility.get("legally_authorized", True))
        return True

    def _lookup_numeric(self, q: str) -> float | int:
        """Return a number from the config numeric map."""
        for key, val in self.numeric_map.items():
            if key in q:
                return val
        if "experience" in q:
            return self.background.get("years_of_experience", 2)
        if "notice" in q:
            return self.background.get("notice_period_days", 0)
        if "salary" in q or "ctc" in q or "compensation" in q:
            return self.background.get("expected_salary", 600000)
        return 0

    def _dropdown_hint(self, q: str) -> str:
        """Return a single-word hint for dropdown matching."""
        if "country" in q:
            return self.personal.get("country", "India")
        if "currency" in q:
            return self.background.get("currency", "INR")
        if "education" in q or "degree" in q:
            return self.background.get("highest_education", "Bachelor")
        if "experience" in q:
            return str(self.background.get("years_of_experience", 2))
        return ""

    def _free_text_answer(self, q: str) -> str:
        """Return a STAR answer or sensible fallback for free-text fields."""
        for key, answer in self.star_map.items():
            # Require whole-word matches to avoid substring false positives
            if any(re.search(r"\b" + re.escape(word) + r"\b", q) for word in key.split()):
                return answer.strip()

        # Specific common fields
        if "first name" in q:
            return self.personal.get("first_name", "")
        if "last name" in q or "surname" in q:
            return self.personal.get("last_name", "")
        if "email" in q:
            return self.personal.get("email", "")
        if "phone" in q or "mobile" in q:
            return self.personal.get("phone", "")
        if "city" in q:
            return self.personal.get("city", "Bangalore")
        if "linkedin" in q:
            return self.personal.get("linkedin_profile", "")
        if "github" in q:
            return self.personal.get("github_url", "")
        if "portfolio" in q or "website" in q:
            return self.personal.get("portfolio_url", "")
        if "salary" in q or "ctc" in q or "compensation" in q:
            return str(self.background.get("expected_salary", "600000"))
        if "notice" in q:
            return str(self.background.get("notice_period_days", 0))
        if "experience" in q:
            return str(self.background.get("years_of_experience", 2))
        if "cover letter" in q or "motivation" in q:
            return (
                "I am deeply passionate about cybersecurity and incident response. "
                "My hands-on experience with SIEM tools and threat detection aligns "
                "well with this role and I am eager to contribute to your SOC team."
            )
        # Generic fallback
        return (
            "I am a cybersecurity professional with experience in SOC operations, "
            "threat detection, and incident response. I am excited about this "
            "opportunity and look forward to contributing to your team."
        )

    @staticmethod
    def clean_label(text: str) -> str:
        """Strip extra whitespace and asterisks from a form label."""
        return re.sub(r"\s+", " ", text.replace("*", "")).strip()

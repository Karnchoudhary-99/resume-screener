"""Turn resume plain text into a structured :class:`Resume`.

Stages, in order: contact details from the header, section split by
heading, skills from the skills section, and experience years from
date ranges in the experience section. Each stage is pure (text in,
data out) so it is unit-testable without any file I/O.
"""

from __future__ import annotations

import re
from datetime import date

from .models import ContactInfo, Resume

_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(
    r"\+?\d[\d\s().-]{7,}\d"
    # A phone-looking run must contain at least 10 digits.
)
_LINKEDIN_RE = re.compile(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[A-Za-z0-9_.-]+")
_GITHUB_RE = re.compile(r"(?:https?://)?(?:www\.)?github\.com/[A-Za-z0-9_.-]+")


def parse_resume(text: str, source: str = "") -> Resume:
    """Parse resume text into a :class:`Resume`."""
    contact = extract_contact(text)
    return Resume(
        source=source,
        raw_text=text,
        contact=contact,
        sections={},
        skills=[],
        experience_years=0.0,
    )


def extract_contact(text: str) -> ContactInfo:
    """Pull name, email, phone and profile links from resume text."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    email_match = _EMAIL_RE.search(text)
    email = email_match.group(0) if email_match else ""
    linkedin_match = _LINKEDIN_RE.search(text)
    linkedin = linkedin_match.group(0) if linkedin_match else ""
    github_match = _GITHUB_RE.search(text)
    github = github_match.group(0) if github_match else ""
    phone = ""
    for line in lines[:6]:  # Contact details live in the header.
        match = _PHONE_RE.search(line)
        if match and _digit_count(match.group(0)) >= 10:
            phone = _clean_phone(match.group(0))
            break
    return ContactInfo(
        name=_guess_name(lines),
        email=email,
        phone=phone,
        linkedin=linkedin,
        github=github,
    )


def _digit_count(value: str) -> int:
    return sum(ch.isdigit() for ch in value)


def _clean_phone(value: str) -> str:
    return re.sub(r"[().\s]+", " ", value).strip(" -")


def _guess_name(lines: list[str]) -> str:
    """First header line that looks like a person's name."""
    for line in lines[:4]:
        lowered = line.lower()
        if "@" in line or "linkedin" in lowered or "github" in lowered:
            continue
        if _PHONE_RE.search(line) and _digit_count(line) >= 10:
            continue
        words = line.replace(",", "").split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words):
            return line
    return ""

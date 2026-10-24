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


#: Heading text (lowercased, punctuation stripped) -> section key.
_HEADINGS = {
    "summary": "summary",
    "profile": "summary",
    "professional summary": "summary",
    "experience": "experience",
    "work experience": "experience",
    "professional experience": "experience",
    "employment": "experience",
    "employment history": "experience",
    "education": "education",
    "academic background": "education",
    "skills": "skills",
    "technical skills": "skills",
    "core skills": "skills",
    "projects": "projects",
    "personal projects": "projects",
    "certifications": "certifications",
    "certificates": "certifications",
    "awards": "awards",
    "publications": "publications",
    "languages": "languages",
}


_MONTHS = {
    name: i + 1
    for i, name in enumerate(
        ["jan", "feb", "mar", "apr", "may", "jun",
         "jul", "aug", "sep", "oct", "nov", "dec"]
    )
}
_DATE_RANGE_RE = re.compile(
    r"(?P<m1>[A-Za-z]{3,9})?\s*(?P<y1>\d{4})\s*[-–—]\s*"
    r"(?:(?P<m2>[A-Za-z]{3,9})\s*)?(?P<y2>\d{4}|present|current|now)",
    re.IGNORECASE,
)


def parse_resume(
    text: str, source: str = "", as_of: date | None = None
) -> Resume:
    """Parse resume text into a :class:`Resume`.

    ``as_of`` fixes "Present" in date ranges (defaults to today);
    pass it in tests so experience years stay deterministic.
    """
    contact = extract_contact(text)
    sections = split_sections(text)
    return Resume(
        source=source,
        raw_text=text,
        contact=contact,
        sections=sections,
        skills=extract_skills(sections.get("skills", "")),
        experience_years=experience_years(
            sections.get("experience", ""), as_of=as_of or date.today()
        ),
    )


def extract_skills(skills_text: str) -> list[str]:
    """Split a skills section into de-duplicated skill names."""
    skills: list[str] = []
    for chunk in re.split(r"[,;|•·\n]", skills_text):
        skill = chunk.strip(" \t-•·")
        # Drop bullet markers and full sentences; skills are short.
        if not skill or len(skill) > 40 or "." in skill:
            continue
        if skill not in skills:
            skills.append(skill)
    return skills


def experience_years(experience_text: str, as_of: date) -> float:
    """Sum the date ranges in the experience section, in years.

    Ranges like ``Jan 2020 - Dec 2022`` or ``2020 - Present`` count
    inclusively by month; overlapping ranges are summed as written
    (a resume-level approximation, documented, not hidden).
    """
    total_months = 0
    for match in _DATE_RANGE_RE.finditer(experience_text):
        start = _month_index(match.group("m1"), int(match.group("y1")))
        end_text = match.group("y2").lower()
        if end_text in {"present", "current", "now"}:
            end = as_of.year * 12 + as_of.month
        else:
            end = _month_index(match.group("m2"), int(match.group("y2")))
        if end >= start:
            total_months += end - start + 1
    return round(total_months / 12, 1)


def _month_index(month_name: str | None, year: int) -> int:
    month = 1
    if month_name:
        month = _MONTHS.get(month_name[:3].lower(), 1)
    return year * 12 + month


def split_sections(text: str) -> dict[str, str]:
    """Split resume text into sections keyed by normalized heading.

    A line is a heading when its normalized text is a known heading, or
    when it is an ALL-CAPS short line (a common resume style) — known
    headings map to a canonical key, unknown ALL-CAPS headings keep a
    slug of their own text instead of being silently dropped.
    """
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        heading = _heading_key(line)
        if heading is not None:
            current = heading
            sections.setdefault(current, [])
            continue
        if current is not None and line:
            sections[current].append(line)
    return {key: "\n".join(lines) for key, lines in sections.items()}


def _heading_key(line: str) -> str | None:
    if not line or len(line) > 60:
        return None
    normalized = re.sub(r"[^a-z0-9 ]+", "", line.lower()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in _HEADINGS:
        return _HEADINGS[normalized]
    # ALL-CAPS short line, e.g. "VOLUNTEERING" — treat as its own section.
    letters = [ch for ch in line if ch.isalpha()]
    if letters and all(ch.isupper() for ch in letters) and len(line.split()) <= 4:
        return normalized.replace(" ", "_")
    return None


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

"""Data model for a parsed resume.

Parsing is deliberately dependency-free and format-agnostic: extractors
turn a file into plain text (see ``extractors``) and the parser turns
that text into this structure. Scoring (a later chunk) reads a
``Resume``, never a raw file, so new formats only need an extractor.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ContactInfo:
    """Contact details pulled from the resume header."""

    name: str = ""
    email: str = ""
    phone: str = ""
    linkedin: str = ""
    github: str = ""


@dataclass
class Resume:
    """Everything the parser knows about one resume."""

    source: str = ""
    raw_text: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    # Section key (e.g. "experience") -> raw section text, in order.
    sections: dict[str, str] = field(default_factory=dict)
    # Skills listed in the skills section, de-duplicated, order kept.
    skills: list[str] = field(default_factory=list)
    # Total years implied by date ranges in the experience section.
    experience_years: float = 0.0

    @property
    def name(self) -> str:
        return self.contact.name

    @property
    def email(self) -> str:
        return self.contact.email

    @property
    def phone(self) -> str:
        return self.contact.phone

    def section(self, key: str, default: str = "") -> str:
        """Return one section's text, or ``default`` if absent."""
        return self.sections.get(key, default)

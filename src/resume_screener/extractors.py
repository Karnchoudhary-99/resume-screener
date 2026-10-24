"""Plain-text extraction from resume files — stdlib only, no deps.

Supported formats:

* ``.txt`` / ``.md`` — read as UTF-8.
* ``.docx`` — a zip of XML; paragraph text lives in
  ``word/document.xml`` as ``<w:t>`` runs, so we unzip and join runs
  into lines. No ``python-docx`` dependency needed.
* ``.pdf`` — text-based PDFs only (not scans). We decompress each
  ``stream`` (FlateDecode, the common case) and pull the strings shown
  by the ``Tj`` / ``TJ`` operators. This covers PDFs produced by most
  word processors and resume builders; scanned/image PDFs carry no
  text layer and are reported honestly as empty rather than guessed.

Anything else raises :class:`UnsupportedFormatError`.
"""

from __future__ import annotations

import re
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

__all__ = ["UnsupportedFormatError", "extract_text"]

_W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_PDF_TJ = re.compile(rb"\((?:[^()\\]|\\.)*\)\s*Tj")
_PDF_TJ_ARRAY = re.compile(rb"\[(?:[^\[\]\\]|\\.)*\]\s*TJ")


class UnsupportedFormatError(ValueError):
    """Raised when a file's extension has no extractor."""


def extract_text(path: str | Path) -> str:
    """Extract plain text from a resume file, dispatching on extension."""
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"resume file not found: {p}")
    suffix = p.suffix.lower()
    if suffix in {".txt", ".md"}:
        return p.read_text(encoding="utf-8", errors="replace")
    if suffix == ".docx":
        return _extract_docx(p)
    if suffix == ".pdf":
        return _extract_pdf(p)
    raise UnsupportedFormatError(
        f"unsupported resume format: {suffix or '(no extension)'} "
        "(supported: .txt, .md, .docx, .pdf)"
    )


def _extract_docx(path: Path) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise ValueError(f"not a valid .docx file: {path}") from exc
    root = ET.fromstring(xml)
    lines: list[str] = []
    for para in root.iter(f"{_W_NS}p"):
        runs = [t.text or "" for t in para.iter(f"{_W_NS}t")]
        lines.append("".join(runs))
    return "\n".join(lines)


def _extract_pdf(path: Path) -> str:
    data = path.read_bytes()
    chunks: list[str] = []
    for match in re.finditer(rb"stream\r?\n(.*?)endstream", data, re.S):
        raw = match.group(1)
        try:
            content = zlib.decompress(raw)
        except zlib.error:
            content = raw  # Uncompressed stream: parse as-is.
        chunks.append(_pdf_stream_text(content))
    return "\n".join(c for c in chunks if c)


def _pdf_stream_text(content: bytes) -> str:
    """Pull the strings a PDF content stream draws with Tj/TJ."""
    parts: list[str] = []
    for match in _PDF_TJ.finditer(content):
        parts.append(_pdf_literal(match.group(0)))
    for match in _PDF_TJ_ARRAY.finditer(content):
        array = match.group(0)
        for string in re.findall(rb"\((?:[^()\\]|\\.)*\)", array):
            parts.append(_pdf_literal(string))
    return " ".join(parts)


def _pdf_literal(token: bytes) -> str:
    """Decode one PDF literal string ``( ... )`` with escapes."""
    # A Tj match carries its operator ("... ) Tj"); pull the string out.
    found = re.search(rb"\((?:[^()\\]|\\.)*\)", token)
    body = found.group(0)[1:-1] if found else token
    out = bytearray()
    i = 0
    while i < len(body):
        c = body[i]
        if c == 0x5C and i + 1 < len(body):  # backslash escape
            nxt = body[i + 1]
            mapping = {ord("n"): 10, ord("r"): 13, ord("t"): 9}
            if nxt in mapping:
                out.append(mapping[nxt])
            elif nxt in (ord("("), ord(")"), 0x5C):
                out.append(nxt)
            # Unknown escapes (e.g. \053 octal) are dropped, not guessed.
            i += 2
        else:
            out.append(c)
            i += 1
    return bytes(out).decode("utf-8", errors="replace")

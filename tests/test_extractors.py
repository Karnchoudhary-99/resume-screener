"""Tests for txt/docx/pdf extraction (stdlib-only extractors)."""

import zipfile
import zlib
from pathlib import Path

import pytest

from resume_screener.extractors import UnsupportedFormatError, extract_text


def _write_docx(path: Path, paragraphs: list[str]) -> None:
    body = "".join(
        f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs
    )
    xml = (
        '<?xml version="1.0"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/'
        'wordprocessingml/2006/main"><w:body>' + body + "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("word/document.xml", xml)


def _write_pdf(path: Path, lines: list[str]) -> None:
    # Minimal text PDF: one Flate-compressed content stream with Tj ops.
    content = "".join(f"BT ({line}) Tj ET\n" for line in lines).encode()
    stream = zlib.compress(content)
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length " + str(len(stream)).encode() + b" /Filter /FlateDecode >>\n"
        b"stream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    path.write_bytes(bytes(out))


def test_txt_extraction(tmp_path):
    p = tmp_path / "resume.txt"
    p.write_text("Asha Patel\nPython developer\n")
    assert "Asha Patel" in extract_text(p)


def test_docx_extraction(tmp_path):
    p = tmp_path / "resume.docx"
    _write_docx(p, ["Asha Patel", "Skills", "Python, FastAPI"])
    text = extract_text(p)
    assert "Asha Patel" in text
    assert "FastAPI" in text


def test_pdf_extraction(tmp_path):
    p = tmp_path / "resume.pdf"
    _write_pdf(p, ["Asha Patel", "Python developer"])
    text = extract_text(p)
    assert "Asha Patel" in text
    assert "Python developer" in text


def test_pdf_escaped_parentheses(tmp_path):
    p = tmp_path / "resume.pdf"
    _write_pdf(p, [r"Acme \(UK\) Ltd"])
    assert "Acme (UK) Ltd" in extract_text(p)


def test_unsupported_format(tmp_path):
    p = tmp_path / "resume.odt"
    p.write_text("x")
    with pytest.raises(UnsupportedFormatError):
        extract_text(p)


def test_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_text(tmp_path / "nope.txt")


def test_corrupt_docx(tmp_path):
    p = tmp_path / "bad.docx"
    p.write_text("not a zip")
    with pytest.raises(ValueError):
        extract_text(p)

"""Command line interface for resume-screener.

Usage:

    resume-screener parse resume.txt
    resume-screener parse resume.pdf --format json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from resume_screener import __version__
from resume_screener.extractors import UnsupportedFormatError, extract_text
from resume_screener.parser import parse_resume


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="resume-screener")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    parse_cmd = sub.add_parser("parse", help="Parse one resume file")
    parse_cmd.add_argument("file", help="Resume file (.txt, .md, .docx, .pdf)")
    parse_cmd.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "parse":
        return _cmd_parse(args)
    parser.print_help()
    return 0


def _cmd_parse(args) -> int:
    try:
        text = extract_text(args.file)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (UnsupportedFormatError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    resume = parse_resume(text, source=args.file)
    if args.format == "json":
        payload = asdict(resume)
        payload["contact"] = asdict(resume.contact)
        print(json.dumps(payload, indent=2))
    else:
        contact = resume.contact
        print(f"Name: {contact.name or '(not found)'}")
        print(f"Email: {contact.email or '(not found)'}")
        print(f"Phone: {contact.phone or '(not found)'}")
        print(f"Experience: {resume.experience_years} years")
        print(f"Skills: {', '.join(resume.skills) or '(none listed)'}")
        print(f"Sections: {', '.join(resume.sections) or '(none)'}")
    return 0

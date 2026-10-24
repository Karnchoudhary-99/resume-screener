"""Command line interface for resume-screener.

Usage:

    resume-screener parse resume.txt
    resume-screener parse resume.pdf --format json
    resume-screener score --job job.json resume1.txt resume2.txt
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from dataclasses import asdict

from resume_screener import __version__
from resume_screener.extractors import UnsupportedFormatError, extract_text
from resume_screener.job import load_job
from resume_screener.parser import parse_resume
from resume_screener.ranking import rank, verdict
from resume_screener.report import anonymize, shortlist, write_csv, write_markdown
from resume_screener.scoring import score_resume


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
    score_cmd = sub.add_parser("score", help="Score resumes against a job")
    score_cmd.add_argument("--job", required=True, help="Job JSON file")
    score_cmd.add_argument(
        "resumes",
        nargs="+",
        help="Resume files to rank (a directory expands to its "
        ".txt/.md/.docx/.pdf files, sorted by name)",
    )
    score_cmd.add_argument(
        "--format", choices=["text", "json"], default="text",
        help="Output format (default: text)",
    )
    score_cmd.add_argument(
        "--top", type=int, default=None,
        help="Show only the top N candidates",
    )
    score_cmd.add_argument(
        "--min-score", type=float, default=None,
        help="Keep only candidates scoring at least this (0-100, inclusive)",
    )
    score_cmd.add_argument(
        "--report-csv", default=None, metavar="PATH",
        help="Write the ranked list (after filtering) to a CSV file",
    )
    score_cmd.add_argument(
        "--report-md", default=None, metavar="PATH",
        help="Write the ranked list (after filtering) to a Markdown file",
    )
    score_cmd.add_argument(
        "--report-json", default=None, metavar="PATH",
        help="Write the ranked list (after filtering) to a JSON file",
    )
    score_cmd.add_argument(
        "--anonymize", action="store_true",
        help="Strip names, emails and source paths (Candidate 1, 2, ...)",
    )
    args = parser.parse_args(argv)
    if args.version:
        print(__version__)
        return 0
    if args.command == "parse":
        return _cmd_parse(args)
    if args.command == "score":
        return _cmd_score(args)
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


SUPPORTED_RESUME_SUFFIXES = {".txt", ".md", ".docx", ".pdf"}


def expand_resume_paths(inputs) -> list[str]:
    """Expand score-CLI inputs to resume files.

    A plain file passes through unchanged. A directory expands to the
    supported resume files directly inside it (not recursive), sorted
    by file name, so a whole folder of applicants scores in one call.
    Other entries inside a directory are skipped, not errors — a folder
    may hold notes or exports next to the resumes. An empty directory
    and a missing path are errors, so a typo never silently scores
    nothing. Duplicates (a file given twice, or inside two dirs) are
    kept once, in first-seen order.
    """
    expanded: list[str] = []
    seen: set[str] = set()  # resolved paths, so the same file via
    # two spellings (./x.txt vs x.txt) still counts once
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            files = sorted(
                (p for p in path.iterdir() if p.is_file()),
                key=lambda p: p.name.lower(),
            )
            files = [p for p in files if p.suffix.lower() in SUPPORTED_RESUME_SUFFIXES]
            if not files:
                raise FileNotFoundError(
                    f"no resume files in directory: {path}"
                )
            for p in files:
                if str(p.resolve()) not in seen:
                    seen.add(str(p.resolve()))
                    expanded.append(str(p))
        elif path.is_file():
            if str(path.resolve()) not in seen:
                seen.add(str(path.resolve()))
                expanded.append(str(path))
        else:
            raise FileNotFoundError(f"resume file not found: {path}")
    return expanded


def _json_payload(ranked) -> list:
    """The ranked list as JSON-ready dicts (stdout and --report-json share it)."""
    return [
        {
            "rank": i + 1,
            "name": s.resume.name or s.resume.source,
            "email": s.resume.email,
            "score": s.total,
            "verdict": verdict(s.total),
            "components": s.components,
            "matched_skills": s.matched_skills,
            "missing_skills": s.missing_skills,
            "preferred_matched": s.preferred_matched,
            "explanations": s.explanations,
        }
        for i, s in enumerate(ranked)
    ]


def _cmd_score(args) -> int:
    try:
        job = load_job(args.job)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    try:
        resume_paths = expand_resume_paths(args.resumes)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    scores = []
    for path in resume_paths:
        try:
            text = extract_text(path)
        except FileNotFoundError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        except (UnsupportedFormatError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        scores.append(score_resume(parse_resume(text, source=path), job))
    ranked = rank(scores)
    if args.min_score is not None:
        try:
            ranked = shortlist(ranked, args.min_score)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    if args.top is not None:
        if args.top < 0:
            print("error: --top must not be negative", file=sys.stderr)
            return 1
        ranked = ranked[: args.top]
    if args.anonymize:
        ranked = anonymize(ranked)
    try:
        if args.report_csv:
            write_csv(ranked, args.report_csv)
        if args.report_md:
            write_markdown(job.title or "Untitled role", ranked, args.report_md)
        if args.report_json:
            payload = _json_payload(ranked)
            with open(args.report_json, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=2)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if args.format == "json":
        print(json.dumps(_json_payload(ranked), indent=2))
        return 0
    title = job.title or "Untitled role"
    print(f"Ranking for: {title} ({len(ranked)} candidate(s))")
    for i, s in enumerate(ranked, start=1):
        name = s.resume.name or s.resume.source
        print(f"\n{i}. {name} — {s.total:.1f}/100 ({verdict(s.total)})")
        if s.components:
            breakdown = ", ".join(
                f"{k} {v * 100:.0f}%" for k, v in s.components.items()
            )
            print(f"   Components: {breakdown}")
        if s.matched_skills:
            print(f"   Matched: {', '.join(s.matched_skills)}")
        if s.missing_skills:
            print(f"   Missing: {', '.join(s.missing_skills)}")
        for line in s.explanations:
            print(f"   - {line}")
    return 0

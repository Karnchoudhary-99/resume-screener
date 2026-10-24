"""Generate the sample screening report in docs/ from bundled samples.

Usage (from the repo root):

    PYTHONPATH=src python examples/make_report.py

Scores the two bundled sample resumes against examples/job.json, keeps
only candidates at or above 60, and writes docs/sample-report.md and
docs/sample-report.csv. The generated files are committed alongside
this script so the README's sample report is the real output, not a
hand-written mock.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from resume_screener.extractors import extract_text  # noqa: E402
from resume_screener.job import load_job  # noqa: E402
from resume_screener.parser import parse_resume  # noqa: E402
from resume_screener.ranking import rank  # noqa: E402
from resume_screener.report import shortlist, write_csv, write_markdown  # noqa: E402
from resume_screener.scoring import score_resume  # noqa: E402


def main() -> int:
    job = load_job(str(ROOT / "examples" / "job.json"))
    scores = []
    for name in ("sample_resume.txt", "sample_junior.txt"):
        path = ROOT / "examples" / name
        scores.append(score_resume(parse_resume(extract_text(str(path)), source=str(path)), job))
    ranked = shortlist(rank(scores), 60.0)
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    write_markdown(job.title or "Untitled role", ranked, str(docs / "sample-report.md"))
    write_csv(ranked, str(docs / "sample-report.csv"))
    print(f"Wrote {docs / 'sample-report.md'} and {docs / 'sample-report.csv'}")
    print(f"Shortlisted {len(ranked)} of {len(scores)} sample candidate(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

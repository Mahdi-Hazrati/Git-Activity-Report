"""Export a Jalali-dated git activity report to Excel.

    python main.py 1405/05
    python main.py 1405/04/20 1405/05/20
    python main.py 1405/04/20..1405/05/20 --repo E:/Workspaces/... --open
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import excel
import gitlog
import jalali
import report as report_builder

DEFAULT_AUTHORS = ["Mahdi Hazrati", "m.hazrati@sadadtsp.ir", "m.hazrati@sadad.co.ir"]

# Column keys accepted by --hide. Keys are shared across sheets, so hiding
# "descriptions" drops the body column from both Daily and Commits.
HIDEABLE = (
    "first",
    "last",
    "span",
    "weekday",
    "month",
    "author",
    "type",
    "scope",
    "scopes",
    "types",
    "files",
    "added",
    "removed",
    "tasks",
    "titles",
    "title",
    "descriptions",
    "hash",
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="gitreport",
        description="Export git history as a Jalali-dated Excel task list.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Period examples:\n"
            "  1405              whole Jalali year\n"
            "  1405/05           one Jalali month\n"
            "  1405/05/20        a single day\n"
            "  1405/04/20 1405/05/20      a range (two arguments)\n"
            "  1405/04/20..1405/05/20     a range (one argument)\n"
        ),
    )
    parser.add_argument("period", help="Jalali year, month, day, or range")
    parser.add_argument("end", nargs="?", help="optional range end, e.g. 1405/05/20")
    parser.add_argument(
        "--repo", default=".", help="repository path (default: current directory)"
    )
    parser.add_argument("-o", "--output", help="output .xlsx path")
    parser.add_argument(
        "--project", default="SadadTSP", help="project name shown on the report"
    )
    parser.add_argument(
        "--hide",
        default="",
        help="comma-separated columns to omit. Available: "
        + ", ".join(HIDEABLE),
    )
    parser.add_argument(
        "--author",
        action="append",
        help="filter by author name or email; repeatable. "
        "Use --all-authors for everyone.",
    )
    parser.add_argument(
        "--all-authors", action="store_true", help="include every author"
    )
    parser.add_argument(
        "--merges", action="store_true", help="include merge commits"
    )
    parser.add_argument(
        "--current-branch",
        action="store_true",
        help="only the checked-out branch (default scans all branches)",
    )
    parser.add_argument(
        "--open", action="store_true", help="open the workbook when finished"
    )
    return parser.parse_args(argv)


def _resolve_span(args: argparse.Namespace) -> jalali.DateRange:
    if args.end:
        return jalali.parse_range(f"{args.period}..{args.end}")
    return jalali.parse_range(args.period)


def _default_output(span: jalali.DateRange) -> Path:
    slug = span.label.replace("/", "-").replace(" .. ", "_to_").replace(" ", "")
    # Reports collect in temp/ beside the script, keeping the code folder clean.
    return Path(__file__).resolve().parent / "temp" / f"report-{slug}.xlsx"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        span = _resolve_span(args)
    except jalali.JalaliError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    hidden = {part.strip().lower() for part in args.hide.split(",") if part.strip()}
    unknown = sorted(hidden - set(HIDEABLE))
    if unknown:
        print(f"error: unknown --hide column(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"available: {', '.join(HIDEABLE)}", file=sys.stderr)
        return 2

    try:
        repo = gitlog.ensure_repository(Path(args.repo).resolve())
    except gitlog.GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    authors = None if args.all_authors else (args.author or DEFAULT_AUTHORS)

    print(f"Repository : {repo}")
    print(f"Period     : {span.label}  ({span.start} .. {span.end})")
    print(f"Authors    : {', '.join(authors) if authors else 'all'}")

    try:
        commits = gitlog.read_commits(
            repo,
            span,
            authors=authors,
            include_merges=args.merges,
            all_branches=not args.current_branch,
        )
    except gitlog.GitError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not commits:
        print("\nNo commits found for this period.")
        print("Try --all-authors, a wider period, or --merges.")
        return 1

    data = report_builder.build(span.label, args.project, commits)
    destination = Path(args.output) if args.output else _default_output(span)
    try:
        excel.write(data, destination, hidden)
    except PermissionError:
        print(
            f"error: cannot write {destination.name} - it is open in Excel. "
            "Close it and run again, or pass a different -o path.",
            file=sys.stderr,
        )
        return 1

    print(f"\n{len(commits)} commits across {data.active_days} active days")
    print(f"+{data.total_insertions} / -{data.total_deletions} "
          f"in {data.total_files} files")
    print(f"Saved      : {destination}")

    if args.open:
        import os
        os.startfile(destination)  # noqa: S606 - Windows-only convenience flag

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

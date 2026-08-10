"""Report generation shared by the CLI and the GUI.

Neither front-end talks to git or openpyxl directly; both call ``generate``,
so a fix here reaches both at once.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import config
import excel
import gitlog
import jalali
import report as report_builder
from config import Project, Settings
from report import Report


@dataclass
class ProjectResult:
    """Outcome for one project - either a report or the reason there isn't one."""

    project: Project
    report: Report | None = None
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.report is not None and bool(self.report.commits)


@dataclass
class Coverage:
    """The commit dates a project actually has, used to explain empty results."""

    first: str = ""
    last: str = ""
    total: int = 0


@dataclass
class RunResult:
    span: jalali.DateRange
    results: list[ProjectResult]
    output: Path | None = None
    coverage: dict[str, Coverage] = field(default_factory=dict)

    @property
    def successes(self) -> list[ProjectResult]:
        return [r for r in self.results if r.ok]

    @property
    def total_commits(self) -> int:
        return sum(len(r.report.commits) for r in self.successes)


def slug(span: jalali.DateRange) -> str:
    return span.label.replace("/", "-").replace(" .. ", "_to_").replace(" ", "")


def resolve_output(settings: Settings, span: jalali.DateRange) -> Path:
    """Where the workbook goes, honouring a user-supplied file name.

    The name may contain ``{period}``, ``{date}`` or ``{name}`` placeholders.
    """
    folder = Path(settings.output_dir) if settings.output_dir else Path(config.default_output_dir())

    raw = (settings.output_name or "").strip()
    if not raw:
        return folder / f"report-{slug(span)}.xlsx"

    filled = (
        raw.replace("{period}", slug(span))
        .replace("{date}", slug(span))
        .replace("{name}", settings.user_name or "report")
    )
    # Strip anything Windows rejects in a file name.
    for bad in '<>:"/\\|?*':
        filled = filled.replace(bad, "-")
    filled = filled.strip(" .") or f"report-{slug(span)}"
    if not filled.lower().endswith(".xlsx"):
        filled += ".xlsx"
    return folder / filled


def collect(project: Project, span: jalali.DateRange, settings: Settings) -> ProjectResult:
    """Read one project's commits, converting failures into a reportable error."""
    try:
        repo = gitlog.ensure_repository(Path(project.path).resolve())
    except gitlog.GitError as exc:
        return ProjectResult(project=project, error=str(exc))

    authors = None if settings.all_authors else (settings.authors or None)
    try:
        commits = gitlog.read_commits(
            repo,
            span,
            authors=authors,
            include_merges=settings.include_merges,
            all_branches=settings.all_branches,
        )
    except gitlog.GitError as exc:
        return ProjectResult(project=project, error=str(exc))

    # The label renames a single-project report; with several projects each keeps
    # its own name, otherwise every sheet would collide on one title.
    name = project.name or repo.name
    if settings.project_label and len(settings.active_projects) == 1:
        name = settings.project_label
    return ProjectResult(
        project=project,
        report=report_builder.build(span.label, name, commits),
    )


def generate(
    period: str,
    settings: Settings,
    *,
    end: str = "",
    destination: Path | None = None,
    progress=None,
) -> RunResult:
    """Build one workbook covering every enabled project.

    ``progress`` is an optional callable taking a status string, used by the
    GUI to report which project is being read.
    """
    span = jalali.parse_range(f"{period}..{end}" if end else period)
    projects = settings.active_projects
    if not projects:
        raise ValueError("no projects selected")

    results = []
    for project in projects:
        if progress:
            progress(f"Reading {project.name or project.path}...")
        results.append(collect(project, span, settings))

    run = RunResult(span=span, results=results)
    if not run.successes:
        # Nothing matched: find out what these repos DO contain, so the caller
        # can say whether the period or the author filter is at fault.
        for result in results:
            if result.error:
                continue
            try:
                repo = Path(result.project.path).resolve()
                first, last, total = gitlog.date_bounds(repo)
                mine = gitlog.date_bounds(
                    repo, None if settings.all_authors else settings.authors
                )[2]
            except (gitlog.GitError, ValueError):
                continue
            if first:
                run.coverage[result.project.name or result.project.path] = Coverage(
                    first=jalali.format_date(first),
                    last=jalali.format_date(last),
                    total=mine if not settings.all_authors else total,
                )
        return run

    if destination is None:
        destination = resolve_output(settings, span)

    if progress:
        progress("Writing workbook...")
    excel.write_multi(
        [(r.report.project, r.report) for r in run.successes],
        destination,
        set(settings.hidden_columns),
    )
    run.output = destination
    return run

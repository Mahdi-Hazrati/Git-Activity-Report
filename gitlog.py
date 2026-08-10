"""Read commits out of a git repository.

``git log`` is invoked once with a record separator that cannot occur in commit
text, so the output parses unambiguously even when subjects contain newlines,
pipes, or tabs.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from jalali import DateRange

# ASCII control characters: no commit message can contain these.
_RECORD = "\x1e"
_FIELD = "\x1f"

# %b is multi-line and must come last: everything after it on the record would
# otherwise be pushed onto its own lines and be indistinguishable from numstat.
_FIELDS = ["%H", "%h", "%an", "%ae", "%aI", "%cn", "%cI", "%s", "%D", "%P", "%b"]
_FIELD_COUNT = len(_FIELDS)
_FORMAT = _FIELD.join(_FIELDS) + _RECORD

# A record's fields begin at a 40-hex hash sitting at the start of a line; the
# numstat block preceding it never matches, since its lines start with digits.
_HASH_AT_LINE_START = re.compile(rf"(?:\A|(?<=\n))[0-9a-f]{{40}}{_FIELD}")

# Conventional commits: type(scope)!: subject
_CONVENTIONAL = re.compile(
    r"^(?P<type>[a-zA-Z]+)(?:\((?P<scope>[^)]*)\))?(?P<breaking>!)?:\s*(?P<summary>.*)$"
)


class GitError(RuntimeError):
    """Raised when git is missing, or the path is not a repository."""


@dataclass
class Commit:
    hash: str
    short_hash: str
    author_name: str
    author_email: str
    authored_at: datetime
    committer_name: str
    committed_at: datetime
    subject: str
    body: str
    refs: str
    parents: str

    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0
    files: list[str] = field(default_factory=list)
    generated_insertions: int = 0
    generated_deletions: int = 0
    generated_files: list[str] = field(default_factory=list)

    @property
    def is_merge(self) -> bool:
        return len(self.parents.split()) > 1

    @property
    def commit_type(self) -> str:
        match = _CONVENTIONAL.match(self.subject)
        return match.group("type").lower() if match else ""

    @property
    def scope(self) -> str:
        match = _CONVENTIONAL.match(self.subject)
        return (match.group("scope") or "") if match else ""

    @property
    def summary(self) -> str:
        match = _CONVENTIONAL.match(self.subject)
        return match.group("summary") if match else self.subject

    @property
    def branch(self) -> str:
        """Best-effort branch label from the decoration git recorded."""
        if not self.refs:
            return ""
        names = []
        for ref in self.refs.split(","):
            ref = ref.strip()
            if not ref or ref.startswith("tag:"):
                continue
            names.append(ref.split("->")[-1].strip())
        return ", ".join(dict.fromkeys(names))


def _run(repo: Path, args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            check=True,
            # Commit text is UTF-8; never let one bad byte abort the whole run.
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise GitError("git executable not found on PATH") from exc
    except subprocess.CalledProcessError as exc:
        raise GitError(f"git {' '.join(args)} failed: {exc.stderr.strip()}") from exc
    return result.stdout


def ensure_repository(repo: Path) -> Path:
    inside = _run(repo, ["rev-parse", "--is-inside-work-tree"]).strip()
    if inside != "true":
        raise GitError(f"{repo} is not inside a git work tree")
    return Path(_run(repo, ["rev-parse", "--show-toplevel"]).strip())


# Machine-produced files: counting them as authored lines inflates a day's
# totals by orders of magnitude (a regenerated SDK is one command, not a day's
# work), so they are tallied separately.
_GENERATED = re.compile(
    r"(^|/)(src/generated/|generated/|dist/|build/|\.next/|__generated__/)"
    r"|(^|/)(pnpm-lock\.yaml|package-lock\.json|yarn\.lock|openapi-spec\.json)$"
    r"|\.(gen|generated)\.[a-z]+$"
)


def is_generated(path: str) -> bool:
    return bool(_GENERATED.search(path))


def _normalize_path(path: str) -> str:
    """Reduce git's rename shorthand to the destination path.

    git compacts renames as ``src/{old => new}/file.ts`` (or ``old => new`` for
    a whole path), which is unreadable in a spreadsheet cell.
    """
    if "=>" not in path:
        return path
    if "{" in path and "}" in path:
        head, _, rest = path.partition("{")
        inner, _, tail = rest.partition("}")
        destination = inner.split("=>")[-1].strip()
        # A rename into the parent directory leaves an empty brace half.
        return f"{head}{destination}{tail}".replace("//", "/")
    return path.split("=>")[-1].strip()


def date_bounds(repo: Path, authors: list[str] | None = None) -> tuple[datetime, datetime, int]:
    """Oldest and newest commit dates, plus the count, ignoring any period.

    Used to tell the user what a repository actually contains when their chosen
    period returns nothing.
    """
    args = ["log", "--all", "--format=%aI"]
    for author in authors or []:
        args.append(f"--author={author}")
    lines = [line for line in _run(repo, args).split() if line]
    if not lines:
        return None, None, 0
    stamps = sorted(datetime.fromisoformat(line) for line in lines)
    return stamps[0], stamps[-1], len(stamps)


def _parse_numstat(block: str, commit: Commit) -> None:
    for line in block.splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        added, removed, path = parts
        path = _normalize_path(path)
        # Binary files report "-" instead of a line count.
        added_lines = int(added) if added.isdigit() else 0
        removed_lines = int(removed) if removed.isdigit() else 0

        if is_generated(path):
            commit.generated_insertions += added_lines
            commit.generated_deletions += removed_lines
            commit.generated_files.append(path)
        else:
            commit.insertions += added_lines
            commit.deletions += removed_lines
            commit.files.append(path)

    commit.files_changed = len(commit.files)


def read_commits(
    repo: Path,
    span: DateRange,
    *,
    authors: list[str] | None = None,
    include_merges: bool = False,
    all_branches: bool = True,
) -> list[Commit]:
    """Collect commits whose author date falls inside ``span``."""
    args = [
        "log",
        f"--pretty=format:{_FORMAT}",
        "--numstat",
        "--date-order",
        # git's --until is exclusive at midnight, so ask for the day after.
        f"--since={span.start.isoformat()} 00:00:00",
        f"--until={span.end.isoformat()} 23:59:59",
    ]
    if all_branches:
        args.append("--all")
    if not include_merges:
        args.append("--no-merges")
    for author in authors or []:
        args.append(f"--author={author}")

    raw = _run(repo, args)
    commits: list[Commit] = []

    # git emits the numstat block *after* the record separator, so each chunk
    # carries the previous commit's stats ahead of its own fields. Parse the
    # fields, then attach the stats found at the head of the following chunk.
    pending: Commit | None = None

    for chunk in raw.split(_RECORD):
        if not chunk.strip():
            continue
        match = _HASH_AT_LINE_START.search(chunk)
        if pending is not None:
            _parse_numstat(chunk[: match.start()] if match else chunk, pending)
            commits.append(pending)
            pending = None
        if match is None:
            continue

        fields = chunk[match.start():].split(_FIELD)
        if len(fields) < _FIELD_COUNT:
            continue
        body = fields[-1]

        commit = Commit(
            hash=fields[0],
            short_hash=fields[1],
            author_name=fields[2],
            author_email=fields[3],
            authored_at=datetime.fromisoformat(fields[4]),
            committer_name=fields[5],
            committed_at=datetime.fromisoformat(fields[6]),
            subject=fields[7],
            refs=fields[8],
            parents=fields[9],
            body=body.strip(),
        )
        pending = commit

    if pending is not None:
        commits.append(pending)

    commits.sort(key=lambda c: c.authored_at)
    return commits

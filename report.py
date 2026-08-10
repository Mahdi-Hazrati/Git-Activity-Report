"""Shape raw commits into the rows each worksheet needs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date

import jalali
from gitlog import Commit


@dataclass
class DailyEntry:
    """One Jalali day's worth of work."""

    day: date
    commits: list[Commit] = field(default_factory=list)

    @property
    def jalali_date(self) -> str:
        return jalali.format_date(self.commits[0].authored_at)

    @property
    def weekday(self) -> str:
        return jalali.weekday_name(self.commits[0].authored_at)

    @property
    def month(self) -> str:
        return jalali.month_name(self.commits[0].authored_at)

    @property
    def first_commit(self) -> str:
        return min(c.authored_at for c in self.commits).strftime("%H:%M")

    @property
    def last_commit(self) -> str:
        return max(c.authored_at for c in self.commits).strftime("%H:%M")

    @property
    def span_hours(self) -> float:
        """Elapsed time between the first and last commit, not effort spent."""
        moments = [c.authored_at for c in self.commits]
        delta = max(moments) - min(moments)
        return round(delta.total_seconds() / 3600, 1)

    @property
    def insertions(self) -> int:
        return sum(c.insertions for c in self.commits)

    @property
    def deletions(self) -> int:
        return sum(c.deletions for c in self.commits)

    @property
    def files_changed(self) -> int:
        # A file touched by two commits in one day is one file of work.
        return len({path for c in self.commits for path in c.files})

    @property
    def scopes(self) -> str:
        found = [c.scope for c in self.commits if c.scope]
        return ", ".join(dict.fromkeys(found))

    @property
    def types(self) -> str:
        found = [c.commit_type for c in self.commits if c.commit_type]
        return ", ".join(dict.fromkeys(found))

    @property
    def tasks(self) -> str:
        return "\n".join(f"- {c.summary}" for c in self.commits)

    @property
    def commit_titles(self) -> str:
        """Every raw commit subject for the day, numbered."""
        return "\n".join(
            f"{index}. {c.subject}" for index, c in enumerate(self.commits, start=1)
        )

    @property
    def commit_descriptions(self) -> str:
        """Commit bodies only - the title lives in its own column."""
        return "\n\n".join(c.body for c in self.commits if c.body)


@dataclass
class Report:
    label: str
    project: str
    commits: list[Commit]
    days: list[DailyEntry]

    @property
    def total_insertions(self) -> int:
        return sum(c.insertions for c in self.commits)

    @property
    def total_deletions(self) -> int:
        return sum(c.deletions for c in self.commits)

    @property
    def total_files(self) -> int:
        return len({path for c in self.commits for path in c.files})

    @property
    def generated_insertions(self) -> int:
        return sum(c.generated_insertions for c in self.commits)

    @property
    def generated_files(self) -> int:
        return len({p for c in self.commits for p in c.generated_files})

    @property
    def active_days(self) -> int:
        return len(self.days)

    @property
    def type_breakdown(self) -> list[tuple[str, int]]:
        counter = Counter(c.commit_type or "other" for c in self.commits)
        return counter.most_common()

    @property
    def scope_breakdown(self) -> list[tuple[str, int]]:
        # A commit scoped "store, ui" is work in both areas, so credit each.
        counter: Counter[str] = Counter()
        for commit in self.commits:
            for part in commit.scope.split(","):
                part = part.strip()
                if part:
                    counter[part] += 1
        return counter.most_common()

    @property
    def authors(self) -> list[tuple[str, int]]:
        counter = Counter(c.author_name for c in self.commits)
        return counter.most_common()


def build(label: str, project: str, commits: list[Commit]) -> Report:
    grouped: dict[date, DailyEntry] = {}
    for commit in commits:
        key = commit.authored_at.date()
        grouped.setdefault(key, DailyEntry(day=key)).commits.append(commit)

    days = [grouped[key] for key in sorted(grouped)]
    for entry in days:
        entry.commits.sort(key=lambda c: c.authored_at)

    return Report(label=label, project=project, commits=commits, days=days)

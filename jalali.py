"""Jalali (Persian) calendar parsing and formatting.

Wraps ``jdatetime`` with the input shapes this tool accepts on the CLI:
a whole year (``1405``), a month (``1405/05``), a single day
(``1405/05/20``), or a range (``1405/04/20..1405/05/20``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import jdatetime

# Jalali months are 31 days for the first six, 30 for the next five, and the
# twelfth is 29 or 30 depending on the leap year.
_MONTH_NAMES = (
    "Farvardin",
    "Ordibehesht",
    "Khordad",
    "Tir",
    "Mordad",
    "Shahrivar",
    "Mehr",
    "Aban",
    "Azar",
    "Dey",
    "Bahman",
    "Esfand",
)

_WEEKDAY_NAMES = (
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
)

_SEPARATORS = re.compile(r"[/\-.]")


class JalaliError(ValueError):
    """Raised when a Jalali date or range cannot be understood."""


@dataclass(frozen=True)
class DateRange:
    """An inclusive span of Gregorian dates, plus a human label."""

    start: date
    end: date
    label: str

    def contains(self, moment: datetime) -> bool:
        return self.start <= moment.date() <= self.end


def _parts(text: str) -> list[int]:
    cleaned = _SEPARATORS.sub("/", text.strip()).strip("/")
    if not cleaned:
        raise JalaliError("empty date")
    try:
        return [int(p) for p in cleaned.split("/")]
    except ValueError as exc:
        raise JalaliError(f"{text!r} is not a numeric Jalali date") from exc


def days_in_month(year: int, month: int) -> int:
    if not 1 <= month <= 12:
        raise JalaliError(f"month {month} out of range 1-12")
    if month <= 6:
        return 31
    if month <= 11:
        return 30
    return 30 if jdatetime.date(year, 1, 1).isleap() else 29


def to_gregorian(year: int, month: int, day: int) -> date:
    try:
        return jdatetime.date(year, month, day).togregorian()
    except ValueError as exc:
        raise JalaliError(f"invalid Jalali date {year}/{month:02d}/{day:02d}") from exc


def parse_endpoint(text: str, *, at_end: bool) -> tuple[date, str]:
    """Resolve one side of a range.

    A partial date widens to cover its whole period: ``1405`` means the entire
    year, so as a start it is Farvardin 1 and as an end it is Esfand 29/30.
    """
    values = _parts(text)
    if len(values) > 3:
        raise JalaliError(f"{text!r} has too many components")

    year = values[0]
    if year < 1000:  # tolerate a two-digit shorthand like 05/20 -> 14xx
        raise JalaliError(f"{text!r} must start with a four-digit Jalali year")

    if len(values) == 1:
        month = 12 if at_end else 1
        day = days_in_month(year, month) if at_end else 1
        label = f"{year}"
    elif len(values) == 2:
        month = values[1]
        day = days_in_month(year, month) if at_end else 1
        label = f"{year}/{month:02d}"
    else:
        month, day = values[1], values[2]
        label = f"{year}/{month:02d}/{day:02d}"

    return to_gregorian(year, month, day), label


def parse_range(text: str) -> DateRange:
    """Parse ``1405/05`` or ``1405/04/20..1405/05/20`` into a Gregorian span."""
    raw = text.strip()
    for token in ("..", " to ", "~"):
        if token in raw:
            left, right = raw.split(token, 1)
            start, start_label = parse_endpoint(left, at_end=False)
            end, end_label = parse_endpoint(right, at_end=True)
            if end < start:
                raise JalaliError(f"range end {end_label} precedes start {start_label}")
            return DateRange(start, end, f"{start_label} .. {end_label}")

    start, label = parse_endpoint(raw, at_end=False)
    end, _ = parse_endpoint(raw, at_end=True)
    return DateRange(start, end, label)


def format_date(moment: datetime) -> str:
    j = jdatetime.date.fromgregorian(date=moment.date())
    return f"{j.year}/{j.month:02d}/{j.day:02d}"


def month_name(moment: datetime) -> str:
    return _MONTH_NAMES[jdatetime.date.fromgregorian(date=moment.date()).month - 1]


def weekday_name(moment: datetime) -> str:
    # jdatetime weekday(): Saturday == 0, matching _WEEKDAY_NAMES.
    return _WEEKDAY_NAMES[jdatetime.date.fromgregorian(date=moment.date()).weekday()]


def iter_days(span: DateRange):
    current = span.start
    while current <= span.end:
        yield current
        current += timedelta(days=1)

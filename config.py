"""Persisted settings.

Portable by design: the config sits beside the executable so copying the app
to a USB stick carries its settings along. If that location is not writable
(read-only media, locked network share), it falls back to the user profile.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

APP_NAME = "GitActivityReport"
CONFIG_NAME = "gitreport-config.json"

# Copyright shown in the UI and on the report's Summary sheet.
AUTHOR_TAG = "M4hd1"
COPYRIGHT = f"(c) {AUTHOR_TAG}"


def app_dir() -> Path:
    """Folder holding the running app - the .exe's folder when frozen."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def _fallback_dir() -> Path:
    base = os.environ.get("APPDATA") or os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / APP_NAME


def config_path() -> Path:
    """Prefer a config beside the app; fall back when that folder is read-only."""
    beside = app_dir() / CONFIG_NAME
    if beside.exists():
        return beside
    try:
        probe = app_dir() / f".{CONFIG_NAME}.probe"
        probe.touch()
        probe.unlink()
        return beside
    except OSError:
        fallback = _fallback_dir()
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback / CONFIG_NAME


def default_output_dir() -> str:
    return str(app_dir() / "reports")


@dataclass
class Project:
    name: str
    path: str
    enabled: bool = True


@dataclass
class Settings:
    # Identity is empty on a fresh install; the user fills it in once.
    user_name: str = ""
    user_email: str = ""

    projects: list[Project] = field(default_factory=list)
    output_dir: str = field(default_factory=default_output_dir)
    output_name: str = ""
    hidden_columns: list[str] = field(default_factory=list)
    project_label: str = ""
    all_authors: bool = False
    include_merges: bool = False
    all_branches: bool = True
    open_when_done: bool = True
    last_period: str = ""
    last_end: str = ""

    @property
    def active_projects(self) -> list[Project]:
        return [p for p in self.projects if p.enabled]

    @property
    def authors(self) -> list[str]:
        """Author filters built from the identity fields."""
        return [value for value in (self.user_name, self.user_email) if value.strip()]


def load(path: Path | None = None) -> Settings:
    """Read settings, falling back to defaults if absent or corrupt."""
    target = path or config_path()
    if not target.exists():
        return Settings()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        # A damaged config must never stop the app from starting.
        return Settings()
    if not isinstance(raw, dict):
        return Settings()

    projects = [
        Project(
            name=str(item.get("name", "")),
            path=str(item.get("path", "")),
            enabled=bool(item.get("enabled", True)),
        )
        for item in raw.get("projects", [])
        if isinstance(item, dict) and item.get("path")
    ]

    fields = Settings().__dataclass_fields__
    values = {}
    for key, spec in fields.items():
        if key in ("projects",) or key not in raw:
            continue
        expected = list if spec.type.startswith("list") else type(getattr(Settings(), key))
        if isinstance(raw[key], expected):
            values[key] = raw[key]
    return Settings(projects=projects, **values)


def save(settings: Settings, path: Path | None = None) -> Path:
    target = path or config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(settings), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return target

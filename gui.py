"""Desktop front-end for the git activity report.

    python gui.py

Generation runs on a worker thread so the window stays responsive; the worker
never touches widgets directly, it posts results back via ``after``.
"""

from __future__ import annotations

import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import config
import gitlog
import jalali
import service
from config import Project, Settings

PAD = 10
VERSION = "v1.0"
MUTED = "#6B7280"
BADGE = "#1F3864"

HIDEABLE = [
    ("weekday", "Weekday"),
    ("month", "Month"),
    ("first", "First commit time"),
    ("last", "Last commit time"),
    ("span", "Span (hours)"),
    ("author", "Author"),
    ("type", "Type"),
    ("scope", "Scope"),
    ("scopes", "Scopes (daily)"),
    ("types", "Types (daily)"),
    ("files", "Files count"),
    ("added", "Lines added"),
    ("removed", "Lines removed"),
    ("tasks", "Tasks completed"),
    ("titles", "Commit titles"),
    ("title", "Commit title"),
    ("descriptions", "Commit descriptions"),
    ("hash", "Commit hash"),
]


class ReportApp(ttk.Frame):
    def __init__(self, master: tk.Tk) -> None:
        super().__init__(master, padding=PAD)
        self.settings: Settings = config.load()
        self.queue: queue.Queue = queue.Queue()
        self.running = False

        self.grid(sticky="nsew")
        master.columnconfigure(0, weight=1)
        master.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # the project list absorbs extra height

        self._build_identity()
        self._build_period()
        self._build_projects()
        self._build_options()
        self._build_actions()
        self._build_footer()
        self._load_settings_into_widgets()
        self._poll_queue()
        self.after(200, self._prompt_first_run)

    # ---------------------------------------------------------------- layout

    def _build_period(self) -> None:
        box = ttk.LabelFrame(self, text="Period (Jalali)", padding=PAD)
        box.grid(row=1, column=0, sticky="ew", pady=(0, PAD))
        box.columnconfigure(1, weight=1)
        box.columnconfigure(3, weight=1)

        ttk.Label(box, text="From").grid(row=0, column=0, sticky="w")
        self.period_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.period_var).grid(
            row=0, column=1, sticky="ew", padx=(6, PAD)
        )

        ttk.Label(box, text="To (optional)").grid(row=0, column=2, sticky="w")
        self.end_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.end_var).grid(row=0, column=3, sticky="ew", padx=6)

        hint = ttk.Label(
            box,
            text="1405 = whole year    1405/05 = one month    1405/05/20 = one day",
            foreground="#6B7280",
        )
        hint.grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

        quick = ttk.Frame(box)
        quick.grid(row=2, column=0, columnspan=4, sticky="w", pady=(6, 0))
        for label, handler in (
            ("This month", self._quick_month),
            ("Last month", self._quick_last_month),
            ("This year", self._quick_year),
        ):
            ttk.Button(quick, text=label, command=handler).pack(side="left", padx=(0, 6))

    def _build_projects(self) -> None:
        box = ttk.LabelFrame(self, text="Projects", padding=PAD)
        box.grid(row=2, column=0, sticky="nsew", pady=(0, PAD))
        box.columnconfigure(0, weight=1)
        box.rowconfigure(0, weight=1)

        columns = ("name", "path")
        self.tree = ttk.Treeview(box, columns=columns, show="tree headings", height=7)
        self.tree.heading("#0", text="On")
        self.tree.heading("name", text="Project")
        self.tree.heading("path", text="Path")
        self.tree.column("#0", width=44, stretch=False, anchor="center")
        self.tree.column("name", width=170, stretch=False)
        self.tree.column("path", width=430)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<Button-1>", self._toggle_click)
        self.tree.bind("<Double-1>", lambda _event: self._toggle_selected())

        scroll = ttk.Scrollbar(box, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        buttons = ttk.Frame(box)
        buttons.grid(row=1, column=0, columnspan=2, sticky="w", pady=(PAD, 0))
        for label, handler in (
            ("Add project...", self._add_project),
            ("Scan folder...", self._scan_folder),
            ("Remove", self._remove_project),
            ("Enable all", lambda: self._set_all(True)),
            ("Disable all", lambda: self._set_all(False)),
        ):
            ttk.Button(buttons, text=label, command=handler).pack(side="left", padx=(0, 6))

    def _build_identity(self) -> None:
        box = ttk.LabelFrame(self, text="Your details", padding=PAD)
        box.grid(row=0, column=0, sticky="ew", pady=(0, PAD))
        box.columnconfigure(1, weight=1)
        box.columnconfigure(3, weight=1)

        ttk.Label(box, text="Name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar()
        self.name_entry = ttk.Entry(box, textvariable=self.name_var)
        self.name_entry.grid(row=0, column=1, sticky="ew", padx=(6, PAD))

        ttk.Label(box, text="Email").grid(row=0, column=2, sticky="w")
        self.email_var = tk.StringVar()
        self.email_entry = ttk.Entry(box, textvariable=self.email_var)
        self.email_entry.grid(row=0, column=3, sticky="ew", padx=6)

        self.all_authors_var = tk.BooleanVar()
        ttk.Checkbutton(
            box,
            text="Report on everyone instead of just me",
            variable=self.all_authors_var,
            command=self._sync_authors_state,
        ).grid(row=1, column=0, columnspan=4, sticky="w", pady=(6, 0))

        ttk.Label(
            box,
            text="Used to match your commits. Both name and email are matched.",
            foreground=MUTED,
        ).grid(row=2, column=0, columnspan=4, sticky="w")

    def _build_options(self) -> None:
        box = ttk.LabelFrame(self, text="Output", padding=PAD)
        box.grid(row=3, column=0, sticky="ew", pady=(0, PAD))
        box.columnconfigure(1, weight=1)

        ttk.Label(box, text="Folder").grid(row=0, column=0, sticky="w")
        self.output_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.output_var).grid(row=0, column=1, sticky="ew", padx=6)
        ttk.Button(box, text="Browse...", command=self._pick_output).grid(
            row=0, column=2, sticky="w"
        )

        ttk.Label(box, text="File name").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.filename_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.filename_var).grid(
            row=1, column=1, sticky="ew", padx=6, pady=(6, 0)
        )
        ttk.Label(box, text=".xlsx optional", foreground=MUTED).grid(
            row=1, column=2, sticky="w", pady=(6, 0)
        )
        ttk.Label(
            box,
            text="Leave blank for report-<period>.  {period} and {name} are replaced.",
            foreground=MUTED,
        ).grid(row=2, column=0, columnspan=3, sticky="w", pady=(2, 0))

        ttk.Label(box, text="Report title").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.label_var = tk.StringVar()
        ttk.Entry(box, textvariable=self.label_var).grid(
            row=3, column=1, sticky="ew", padx=6, pady=(6, 0)
        )
        ttk.Label(box, text="blank = project name", foreground=MUTED).grid(
            row=3, column=2, sticky="w", pady=(6, 0)
        )

        toggles = ttk.Frame(box)
        toggles.grid(row=4, column=0, columnspan=3, sticky="w", pady=(8, 0))
        self.merges_var = tk.BooleanVar()
        self.branches_var = tk.BooleanVar()
        self.open_var = tk.BooleanVar()
        for text, var in (
            ("Include merge commits", self.merges_var),
            ("Scan all branches", self.branches_var),
            ("Open when finished", self.open_var),
        ):
            ttk.Checkbutton(toggles, text=text, variable=var).pack(side="left", padx=(0, 14))

        ttk.Button(box, text="Choose columns...", command=self._pick_columns).grid(
            row=5, column=0, sticky="w", pady=(8, 0)
        )
        self.columns_label = ttk.Label(box, text="", foreground=MUTED)
        self.columns_label.grid(row=5, column=1, columnspan=2, sticky="w", pady=(8, 0))

    def _build_actions(self) -> None:
        bar = ttk.Frame(self)
        bar.grid(row=4, column=0, sticky="ew")
        bar.columnconfigure(1, weight=1)

        self.generate_button = ttk.Button(
            bar, text="Generate report", command=self._generate
        )
        self.generate_button.grid(row=0, column=0, sticky="w")

        self.status = ttk.Label(bar, text="Ready", foreground="#6B7280")
        self.status.grid(row=0, column=1, sticky="w", padx=PAD)

        self.progress = ttk.Progressbar(bar, mode="indeterminate", length=140)
        self.progress.grid(row=0, column=2, sticky="e")

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(0, PAD, 0, 0))
        footer.grid(row=5, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        ttk.Separator(footer, orient="horizontal").grid(
            row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6)
        )
        ttk.Label(
            footer,
            text=f"Git Activity Report  {VERSION}",
            foreground=MUTED,
        ).grid(row=1, column=0, sticky="w")

        badge = ttk.Label(
            footer,
            text=f"{config.COPYRIGHT}",
            foreground=BADGE,
            font=("Segoe UI Semibold", 9),
        )
        badge.grid(row=1, column=1, sticky="e")

    def _prompt_first_run(self) -> None:
        """Nudge for identity once, so a fresh install isn't silently unfiltered."""
        if self.settings.user_name or self.settings.user_email or self.all_authors_var.get():
            return
        self.name_entry.focus_set()
        self.status.configure(
            text="Enter your name and email to match your commits", foreground="#B45309"
        )

    # --------------------------------------------------------------- helpers

    def _load_settings_into_widgets(self) -> None:
        settings = self.settings
        self.period_var.set(settings.last_period)
        self.end_var.set(settings.last_end)
        self.name_var.set(settings.user_name)
        self.email_var.set(settings.user_email)
        self.all_authors_var.set(settings.all_authors)
        self.output_var.set(settings.output_dir or config.default_output_dir())
        self.filename_var.set(settings.output_name)
        self.label_var.set(settings.project_label)
        self.merges_var.set(settings.include_merges)
        self.branches_var.set(settings.all_branches)
        self.open_var.set(settings.open_when_done)
        self.hidden = set(settings.hidden_columns)
        self._refresh_tree()
        self._sync_authors_state()
        self._refresh_columns_label()

    def _refresh_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        for index, project in enumerate(self.settings.projects):
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                text="[x]" if project.enabled else "[  ]",
                values=(project.name, project.path),
            )

    def _refresh_columns_label(self) -> None:
        count = len(self.hidden)
        self.columns_label.configure(
            text="All columns shown" if not count else f"{count} column(s) hidden"
        )

    def _sync_authors_state(self) -> None:
        state = "disabled" if self.all_authors_var.get() else "normal"
        self.name_entry.configure(state=state)
        self.email_entry.configure(state=state)

    def _toggle_click(self, event: tk.Event) -> None:
        # Only the checkbox column toggles; elsewhere behaves as normal selection.
        if self.tree.identify_column(event.x) == "#0":
            item = self.tree.identify_row(event.y)
            if item:
                self._toggle(int(item))

    def _toggle_selected(self) -> None:
        for item in self.tree.selection():
            self._toggle(int(item))

    def _toggle(self, index: int) -> None:
        project = self.settings.projects[index]
        project.enabled = not project.enabled
        self._refresh_tree()

    def _set_all(self, enabled: bool) -> None:
        for project in self.settings.projects:
            project.enabled = enabled
        self._refresh_tree()

    # ----------------------------------------------------------- project ops

    def _add_project(self) -> None:
        folder = filedialog.askdirectory(title="Select a git repository")
        if folder:
            self._add_repo(Path(folder), announce=True)

    def _scan_folder(self) -> None:
        """Add every git repository nested under a chosen folder."""
        folder = filedialog.askdirectory(title="Select a folder to scan")
        if not folder:
            return
        root = Path(folder)
        found = sorted({p.parent for p in root.glob("*/.git")} | {p.parent for p in root.glob("*/*/.git")} | {p.parent for p in root.glob("*/*/*/.git")})
        added = sum(1 for repo in found if self._add_repo(repo, announce=False))
        self._refresh_tree()
        messagebox.showinfo(
            "Scan complete",
            f"Found {len(found)} repositories, added {added} new."
            if found
            else "No git repositories found in that folder.",
        )

    def _add_repo(self, folder: Path, *, announce: bool) -> bool:
        """Add a repository if it is valid and not already listed.

        Named to avoid tkinter's internal Widget._register, which after() uses.
        """
        resolved = str(folder.resolve())
        if any(p.path == resolved for p in self.settings.projects):
            if announce:
                messagebox.showinfo("Already added", "That project is already listed.")
            return False
        try:
            gitlog.ensure_repository(folder)
        except gitlog.GitError as exc:
            if announce:
                messagebox.showerror("Not a repository", str(exc))
            return False
        self.settings.projects.append(Project(name=folder.name, path=resolved))
        if announce:
            self._refresh_tree()
        return True

    def _remove_project(self) -> None:
        indexes = sorted((int(item) for item in self.tree.selection()), reverse=True)
        if not indexes:
            messagebox.showinfo("Nothing selected", "Select a project to remove.")
            return
        for index in indexes:
            del self.settings.projects[index]
        self._refresh_tree()

    def _pick_output(self) -> None:
        folder = filedialog.askdirectory(title="Where should reports be saved?")
        if folder:
            self.output_var.set(folder)

    def _pick_columns(self) -> None:
        ColumnDialog(self, self.hidden, self._apply_columns)

    def _apply_columns(self, hidden: set[str]) -> None:
        self.hidden = hidden
        self._refresh_columns_label()

    # ------------------------------------------------------------- shortcuts

    def _today(self):
        import jdatetime
        return jdatetime.date.today()

    def _quick_month(self) -> None:
        today = self._today()
        self.period_var.set(f"{today.year}/{today.month:02d}")
        self.end_var.set("")

    def _quick_last_month(self) -> None:
        today = self._today()
        year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
        self.period_var.set(f"{year}/{month:02d}")
        self.end_var.set("")

    def _quick_year(self) -> None:
        self.period_var.set(str(self._today().year))
        self.end_var.set("")

    # ------------------------------------------------------------ generation

    def _collect_settings(self) -> Settings:
        settings = self.settings
        settings.user_name = self.name_var.get().strip()
        settings.user_email = self.email_var.get().strip()
        settings.all_authors = self.all_authors_var.get()
        settings.output_dir = self.output_var.get().strip()
        settings.output_name = self.filename_var.get().strip()
        settings.project_label = self.label_var.get().strip()
        settings.include_merges = self.merges_var.get()
        settings.all_branches = self.branches_var.get()
        settings.open_when_done = self.open_var.get()
        settings.hidden_columns = sorted(self.hidden)
        settings.last_period = self.period_var.get().strip()
        settings.last_end = self.end_var.get().strip()
        return settings

    def _generate(self) -> None:
        if self.running:
            return
        settings = self._collect_settings()

        if not settings.last_period:
            messagebox.showwarning("Period required", "Enter a period, e.g. 1405/05.")
            return
        if not settings.active_projects:
            messagebox.showwarning("No projects", "Add and tick at least one project.")
            return
        if not settings.all_authors and not settings.authors:
            messagebox.showwarning(
                "Your details required",
                "Enter your name or email so your commits can be matched,\n"
                "or tick 'Report on everyone instead of just me'.",
            )
            self.name_entry.focus_set()
            return
        try:
            jalali.parse_range(
                f"{settings.last_period}..{settings.last_end}"
                if settings.last_end
                else settings.last_period
            )
        except jalali.JalaliError as exc:
            messagebox.showerror("Invalid period", str(exc))
            return

        if not self._confirm_future_or_stale(settings):
            return

        config.save(settings)
        self.running = True
        self.generate_button.configure(state="disabled")
        self.progress.start(12)
        self.status.configure(text="Working...", foreground="#6B7280")

        threading.Thread(target=self._worker, args=(settings,), daemon=True).start()

    def _worker(self, settings: Settings) -> None:
        try:
            run = service.generate(
                settings.last_period,
                settings,
                end=settings.last_end,
                progress=lambda text: self.queue.put(("status", text)),
            )
            self.queue.put(("done", run))
        except Exception as exc:  # surfaced in the UI rather than a console
            self.queue.put(("error", str(exc)))

    def _poll_queue(self) -> None:
        try:
            while True:
                kind, payload = self.queue.get_nowait()
                if kind == "status":
                    self.status.configure(text=payload)
                elif kind == "done":
                    self._finish(payload)
                elif kind == "error":
                    self._fail(payload)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def _stop_running(self) -> None:
        self.running = False
        self.progress.stop()
        self.generate_button.configure(state="normal")

    def _finish(self, run: service.RunResult) -> None:
        self._stop_running()
        failures = [r for r in run.results if not r.ok]

        if not run.successes:
            self.status.configure(text="No commits found", foreground="#B45309")
            messagebox.showwarning("Nothing to report", self._explain_empty(run))
            return

        summary = f"{run.total_commits} commits from {len(run.successes)} project(s)"
        self.status.configure(text=f"{summary} -> {run.output.name}", foreground="#166534")

        detail = "\n".join(
            f"  {r.project.name}: {len(r.report.commits)} commits" for r in run.successes
        )
        if failures:
            detail += "\n\nSkipped:\n" + "\n".join(
                f"  {r.project.name}: {r.error or 'no commits in this period'}"
                for r in failures
            )
        messagebox.showinfo("Report ready", f"{summary}\n\n{detail}\n\nSaved to:\n{run.output}")

        if self.open_var.get():
            self._open(run.output)

    def _confirm_future_or_stale(self, settings: Settings) -> bool:
        """Warn on a period that is entirely in the past or future year.

        A mistyped year (1404 for 1405) is the most common cause of an empty
        report, and it is much cheaper to question here than after a full scan.
        """
        import jdatetime

        this_year = jdatetime.date.today().year
        years = set()
        for value in (settings.last_period, settings.last_end):
            head = value.strip().replace("-", "/").replace(".", "/").split("/")[0]
            if head.isdigit():
                years.add(int(head))
        if not years or this_year in years:
            return True

        span = ", ".join(str(y) for y in sorted(years))
        return messagebox.askyesno(
            "Check the year",
            f"The period you entered is for year {span}, but this year is "
            f"{this_year}.\n\nA mistyped year is the usual reason a report comes "
            "back empty.\n\nGenerate anyway?",
            icon="question",
        )

    def _explain_empty(self, run: service.RunResult) -> str:
        """Say which of period / author / repo is actually to blame."""
        lines = [f"No commits found for {run.span.label}."]

        broken = [r for r in run.results if r.error]
        if broken:
            lines.append("\nThese projects could not be read:")
            lines += [f"  {r.project.name}: {r.error}" for r in broken]

        if run.coverage:
            has_dates = any(c.total for c in run.coverage.values())
            no_match = any(not c.total for c in run.coverage.values())

            lines.append(
                "\nWhat these projects actually contain:"
                if has_dates and no_match
                else "\nThese projects have commits, but outside your period:"
                if has_dates
                else "\nThese projects have history, but none matching you:"
            )
            for name, cover in run.coverage.items():
                if cover.total:
                    lines.append(f"  {name}: {cover.first} to {cover.last}")
                else:
                    lines.append(f"  {name}: no commits by you")
            lines.append("")
            if has_dates:
                lines.append("Fix: set the period to a range shown above.")
            if no_match:
                lines.append(
                    "Fix: check your name/email spelling, or tick "
                    "'Report on everyone instead of just me'."
                )
        return "\n".join(lines)

    def _fail(self, message: str) -> None:
        self._stop_running()
        self.status.configure(text="Failed", foreground="#B91C1C")
        messagebox.showerror("Could not generate report", message)

    def _open(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", "", str(path)], shell=False)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as exc:
            messagebox.showwarning("Could not open file", str(exc))


class ColumnDialog(tk.Toplevel):
    """Tick the columns to include; unticked ones are hidden."""

    def __init__(self, parent: ReportApp, hidden: set[str], on_apply) -> None:
        super().__init__(parent)
        self.title("Choose columns")
        self.transient(parent.winfo_toplevel())
        self.resizable(False, False)
        self.on_apply = on_apply

        frame = ttk.Frame(self, padding=PAD)
        frame.grid(sticky="nsew")
        ttk.Label(frame, text="Ticked columns appear in the report.").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 8)
        )

        self.vars: dict[str, tk.BooleanVar] = {}
        half = (len(HIDEABLE) + 1) // 2
        for index, (key, label) in enumerate(HIDEABLE):
            var = tk.BooleanVar(value=key not in hidden)
            self.vars[key] = var
            ttk.Checkbutton(frame, text=label, variable=var).grid(
                row=1 + index % half, column=index // half, sticky="w", padx=(0, 18)
            )

        buttons = ttk.Frame(frame)
        buttons.grid(row=half + 2, column=0, columnspan=2, sticky="e", pady=(PAD, 0))
        ttk.Button(buttons, text="Select all", command=lambda: self._set_all(True)).pack(
            side="left", padx=(0, 6)
        )
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="OK", command=self._apply).pack(side="left")

        self.grab_set()

    def _set_all(self, value: bool) -> None:
        for var in self.vars.values():
            var.set(value)

    def _apply(self) -> None:
        self.on_apply({key for key, var in self.vars.items() if not var.get()})
        self.destroy()


def main() -> int:
    root = tk.Tk()
    root.title("Git Activity Report")
    root.minsize(760, 620)
    style = ttk.Style()
    if "vista" in style.theme_names():
        style.theme_use("vista")
    ReportApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

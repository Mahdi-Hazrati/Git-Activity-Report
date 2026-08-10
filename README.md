# Git Activity Report
<img width="762" height="817" alt="GitActivityReport_0NoHkPiBsZ" src="https://github.com/user-attachments/assets/e33d712d-7501-49e0-bd4e-1c7f84be466f" />

Turns git history into a styled Excel report, dated in the **Jalali (Persian)** calendar.
Built for handing a manager a clear picture of what was worked on, and when.

Works three ways — a **portable .exe** needing nothing installed, a **desktop app**
from source, or the **command line** for scripting. All share one engine, so every
route produces identical reports.

---

## 1. The portable app (no install)

Grab **`dist/GitActivityReport.exe`** and run it. One file, ~23 MB, no Python
required. Copy it to a USB stick, a colleague's laptop, anywhere.

The only requirement on the target machine is **git** — the report is read from
real repositories, so git must be installed and on the PATH.

Settings and reports stay **beside the .exe** (`gitreport-config.json` and
`reports/`), so the whole thing travels together. If the exe sits somewhere
read-only, settings fall back to your user folder automatically.

### Rebuilding it

```bash
pip install -r requirements.txt
python build_exe.py
```

---

## 2. Setup from source

```bash
cd tmp/gitreport
pip install -r requirements.txt
```

Requires **Python 3.9+** and `git` on your PATH.

---

## 3. Using the app

Run the .exe, double-click **`Report GUI.bat`**, or:

```bash
python gui.py
```

Then:

1. **Your details** — enter your name and email. These match your commits, so
   the report covers your work only. Tick **Report on everyone** for the whole team.
2. **Period** — type a Jalali period, or press **This month** / **Last month** /
   **This year**.
3. **Projects** — **Add project...** to pick a repository, or **Scan folder...**
   to find every repo nested under one folder. Tick the ones to include (click the
   `[x]`, or double-click a row).
4. **Output** — choose the folder, the file name, and the report title. Leave the
   file name blank for `report-<period>.xlsx`, or use `{period}` and `{name}`
   placeholders. **Choose columns...** picks exactly which columns appear.
5. **Generate report.**

Everything is saved and restored next launch, so routine runs are two clicks.

Multiple projects go into **one workbook**: an **Overview** sheet comparing them,
then each project's own four sheets.

---

## 4. Command line

```bash
cd tmp/gitreport

python main.py 1405/05                    # one month
python main.py 1405/04/20 1405/05/20      # a date range
```

The report lands in `temp/` next to the script:

```text
temp/report-1405-04-20_to_1405-05-20.xlsx
```

> **All dates you type are Jalali.** Never pass Gregorian dates — `2026/08/09`
> would be read as Jalali year 2026 and return nothing.

The CLI reports on one repository at a time (`--repo`); for multiple projects in
a single workbook, use the desktop app.

---

## 5. Choosing the period

You can pass a **year**, **month**, or **day** — a partial date automatically
widens to cover its whole period.

| What you type | What you get |
| --- | --- |
| `1405` | the entire Jalali year |
| `1405/05` | all of Mordad 1405 |
| `1405/05/20` | that single day |
| `1405/04/20 1405/05/20` | a range (two arguments) |
| `1405/04/20..1405/05/20` | the same range (one argument) |

`/`, `-`, and `.` all work as separators, so `1405-05` is the same as `1405/05`.

The end date must come **after** the start, and the year is always four digits.
Both rules are enforced with a plain error message rather than a silent empty report.

---

## 6. Common options

| Flag | What it does |
| --- | --- |
| `-o <path>` | write to a specific file instead of `temp/` |
| `--project <name>` | project name in the title (default: `SadadTSP`) |
| `--hide <cols>` | drop columns you don't want (see §8) |
| `--all-authors` | include the whole team, not just you |
| `--author "<name>"` | filter by a specific person; repeatable |
| `--repo <path>` | report on a different repository |
| `--open` | open the file in Excel when it finishes |
| `--merges` | include merge commits (excluded by default) |
| `--current-branch` | only the checked-out branch (default: all branches) |
| `-h` | full help |

Examples:

```bash
# Whole team, one month, opened when ready
python main.py 1405/05 --all-authors --open

# Another repo, custom name and output path
python main.py 1405 --repo ../../other-project --project "Other App" -o boss.xlsx
```

The CLI's default author filter lives in `DEFAULT_AUTHORS` at the top of `main.py`.
The app instead uses whatever name and email you enter under **Your details**, so
a fresh install has no identity baked in.

---

## 7. What's in the workbook

**Summary** — the sheet to show a manager. Totals, then four sections with inline
bar charts: what was built by area, type of work with percentages, daily activity,
and commit titles per day (click **[+]** in the left margin to expand a day).

**Daily Task List** — one row per working day: commit count, first/last commit
time, files touched, lines added/removed, and the day's tasks. Thursdays and
Fridays are shaded.

**Commits** — one row per commit: date, time, author, type, scope, title,
description, file and line counts, short hash.

**Changed Files** — one row per commit with its files collapsed underneath.
Click **[+]** to expand.

---

## 8. Hiding columns

```bash
python main.py 1405/05 --hide first,last,span
python main.py 1405/05 --hide weekday,month,hash,descriptions
```

Available keys:

```text
first  last  span  weekday  month  author  type  scope  scopes
types  files  added  removed  tasks  titles  title  descriptions  hash
```

Keys apply across sheets — `--hide descriptions` removes that column from both
**Daily Task List** and **Commits**. A misspelled key stops the run and prints
the valid list, so a typo never silently produces the wrong report.

---

## 9. Reading the numbers correctly

Three things worth understanding before sending a report to a manager.

**Generated code is excluded.** Machine-produced files — `openapi-spec.json`,
anything under `src/generated/`, `*.gen.ts`, lockfiles — are counted separately
and disclosed on their own Summary line. Without this, one day in Mordad 1405
showed *+52,141 lines from 2 commits*, which was a regenerated API client rather
than a day's work. The headline totals are hand-written code only.

**"Span (h)" is elapsed time, not hours worked.** It measures first commit to
last commit that day, so two commits a minute apart show `0`. It is not a timesheet.

**"Commit Description" is often empty.** It holds the commit *body*, and most
commits here are subject-only — in one 150-commit report just 9 had a body.
That column fills up only if you start writing multi-line commit messages.

---

## 10. Troubleshooting

**"No commits found for this period."**
Usually the author filter or the period. Try `--all-authors`, widen the range, or
check the repo's actual history:

```bash
git log --format=%aI | tail -1     # oldest commit (Gregorian)
```

**"cannot write ... it is open in Excel"**
Close the workbook and re-run, or pass a different `-o` path.

**"range end ... precedes start"**
The two dates are backwards, or the end year has a typo — e.g. `1404` where
`1405` was meant.

**"is not a git repository"**
Run from inside the repo, or point at it with `--repo <path>`. In the app, the
project is skipped and the reason is listed when the run finishes.

**The app won't start / no window appears**
Run `python gui.py` from a terminal to see the error. If it reports no module
named `tkinter`, reinstall Python with the "tcl/tk and IDLE" option ticked.

**A project shows as skipped**
Either it has no commits in that period, or the author filter excluded them all.
Tick **Everyone** to confirm which.

**Reset the app to defaults**
Delete `gitreport-config.json`. A corrupt config is ignored automatically rather
than crashing the app.

---

## 11. How the code is organised

| File | Responsibility |
| --- | --- |
| `gui.py` | desktop app (tkinter); runs generation on a worker thread |
| `main.py` | CLI parsing, validation, wiring |
| `service.py` | shared engine both front-ends call |
| `config.py` | settings, portable paths, `gitreport-config.json` |
| `build_exe.py` | builds the portable single-file executable |
| `jalali.py` | Jalali parsing, conversion, formatting |
| `gitlog.py` | runs `git log`, parses commits and file stats |
| `report.py` | groups commits per day, computes totals |
| `excel.py` | renders the worksheets |

The GUI and CLI both call `service.generate`, so neither duplicates logic and a
fix reaches both at once.

Reports are written to `temp/` when run from source, or `reports/` beside the
`.exe`. Either is created automatically. The whole `tmp/` folder is gitignored,
so nothing here — including your config — is ever committed.

---

## 12. Credits

Git Activity Report — **(c) M4hd1**

The attribution appears in the app footer, on the report's Summary sheet, and in
the workbook's file properties.

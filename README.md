# Git Activity Report

<div align="center">

**Turn Git history into a polished Excel activity report using the Jalali (Persian) calendar.**

Built for developers who need to give managers a clear picture of what was worked on—and when.

<img width="762" height="817" alt="GitActivityReport_0NoHkPiBsZ" src="https://github.com/user-attachments/assets/a736e10d-bbe3-4ded-990e-154e6142ede0" />

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-v1.0.0-0078D4?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/Mahdi-Hazrati/Git-Activity-Report/releases/download/v1.0.0/GitActivityReport.exe)

[![Release](https://img.shields.io/github/v/release/Mahdi-Hazrati/Git-Activity-Report?style=flat-square)](https://github.com/Mahdi-Hazrati/Git-Activity-Report/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](#run-from-source)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D4?style=flat-square&logo=windows11&logoColor=white)](#quick-start)

[Download](#download) · [Quick start](#quick-start) · [Command line](#command-line) · [Workbook contents](#whats-in-the-workbook) · [Troubleshooting](#troubleshooting)

</div>

---

## Overview

Git Activity Report reads real Git repositories and produces a styled `.xlsx` workbook containing summaries, daily activity, commits, and changed files.

Use it in any of three ways:

| Option | Best for | Requirements |
| --- | --- | --- |
| **Portable Windows app** | The fastest start | Git only |
| **Desktop app from source** | Development and customization | Python 3.9+ and Git |
| **Command line** | Scripts and repeatable workflows | Python 3.9+ and Git |

All three routes use the same reporting engine, so they produce identical reports.

## Highlights

- Jalali year, month, day, and custom date-range support
- One-click Windows executable with no Python installation required
- Reports for one developer or the whole team
- Multiple repositories combined into one workbook
- Manager-friendly summary with charts and expandable details
- Configurable workbook columns
- Generated-code detection for more meaningful totals
- Saved desktop settings for fast recurring reports

## Download

### Windows portable app

[![Download Git Activity Report](https://img.shields.io/badge/Download-GitActivityReport.exe-success?style=for-the-badge&logo=github)](https://github.com/Mahdi-Hazrati/Git-Activity-Report/releases/download/v1.0.0/GitActivityReport.exe)

Download **`GitActivityReport.exe`**, then run it—no installer or Python environment is required.

> [!IMPORTANT]
> Git must be installed and available on your system `PATH`. The application reads report data directly from Git repositories.

Settings and reports are stored beside the executable:

```text
GitActivityReport.exe
gitreport-config.json
reports/
```

This makes the app portable: you can keep it on a USB drive or copy it to another computer. If the executable is in a read-only folder, settings automatically fall back to your user folder.

## Quick start

1. [Download `GitActivityReport.exe`](https://github.com/Mahdi-Hazrati/Git-Activity-Report/releases/download/v1.0.0/GitActivityReport.exe).
2. Open the application.
3. Enter your name and email as they appear in your Git commits—or enable **Report on everyone**.
4. Choose a Jalali period using a preset or a custom date.
5. Add one repository, or scan a folder for multiple repositories.
6. Choose the output folder, workbook name, title, and visible columns.
7. Select **Generate report**.

Your settings are restored the next time the app starts, so routine reports usually take only two clicks.

When multiple projects are selected, the app creates **one workbook** with an **Overview** sheet followed by four sheets for each project.

## Run from source

### Requirements

- Python 3.9 or newer
- Git available on `PATH`

### Installation

```bash
git clone https://github.com/Mahdi-Hazrati/Git-Activity-Report.git
cd Git-Activity-Report
pip install -r requirements.txt
```

### Start the desktop app

Double-click **`Report GUI.bat`**, or run:

```bash
python gui.py
```

### Build the Windows executable

```bash
pip install -r requirements.txt
python build_exe.py
```

The generated executable is written to `dist/GitActivityReport.exe`.

## Command line

Generate a report for one Jalali month:

```bash
python main.py 1405/05
```

Generate a report for a custom Jalali date range:

```bash
python main.py 1405/04/20 1405/05/20
```

By default, the report is written to:

```text
temp/report-1405-04-20_to_1405-05-20.xlsx
```

> [!WARNING]
> Every date entered in the application or CLI must be Jalali. Do not pass a Gregorian date such as `2026/08/09`; it would be interpreted as Jalali year 2026 and would return no results.

The CLI handles one repository at a time with `--repo`. To combine multiple projects in one workbook, use the desktop app.

## Choosing a period

A partial date automatically expands to cover the complete period.

| Input | Result |
| --- | --- |
| `1405` | Entire Jalali year |
| `1405/05` | All of Mordad 1405 |
| `1405/05/20` | One day |
| `1405/04/20 1405/05/20` | Date range using two arguments |
| `1405/04/20..1405/05/20` | The same date range using one argument |

The separators `/`, `-`, and `.` are supported, so `1405-05` is equivalent to `1405/05`.

The end date must be after the start date, and the year must contain four digits. Invalid input produces a clear error instead of a silent empty report.

## Common CLI options

| Option | Description |
| --- | --- |
| `-o <path>` | Write to a specific file instead of `temp/` |
| `--project <name>` | Set the project name in the title; default: `SadadTSP` |
| `--hide <cols>` | Remove selected columns; see [Hiding columns](#hiding-columns) |
| `--all-authors` | Include the whole team |
| `--author "<name>"` | Filter by a specific person; repeatable |
| `--repo <path>` | Report on another repository |
| `--open` | Open the workbook in Excel after generation |
| `--merges` | Include merge commits; excluded by default |
| `--current-branch` | Use only the checked-out branch; all branches are used by default |
| `-h` | Display full help |

### Examples

Create a team report for one month and open it when ready:

```bash
python main.py 1405/05 --all-authors --open
```

Report on another repository with a custom project name and output path:

```bash
python main.py 1405 --repo ../../other-project --project "Other App" -o boss.xlsx
```

The CLI's default author filter is stored in `DEFAULT_AUTHORS` at the top of `main.py`. The desktop app uses the name and email entered under **Your details**, so a fresh installation has no identity built in.

## What's in the workbook

### Summary

The manager-facing sheet. It contains totals and four sections with inline bar charts:

- Work completed by area
- Work type and percentages
- Daily activity
- Commit titles grouped by day

Use the **[+]** control in the left margin to expand a day.

### Daily Task List

One row per working day with commit count, first and last commit time, files touched, lines added and removed, and the day's tasks. Thursdays and Fridays are shaded.

### Commits

One row per commit with date, time, author, type, scope, title, description, file and line counts, and short hash.

### Changed Files

One row per commit with its changed files collapsed below it. Select **[+]** to expand the file list.

## Hiding columns

Remove columns you do not want in the workbook:

```bash
python main.py 1405/05 --hide first,last,span
python main.py 1405/05 --hide weekday,month,hash,descriptions
```

Available keys:

```text
first  last  span  weekday  month  author  type  scope  scopes
types  files  added  removed  tasks  titles  title  descriptions  hash
```

Keys apply across worksheets. For example, `--hide descriptions` removes the description column from both **Daily Task List** and **Commits**.

A misspelled key stops the run and displays the valid list, preventing a typo from silently producing the wrong report.

## Understanding the numbers

### Generated code is excluded

Machine-generated files—such as `openapi-spec.json`, files under `src/generated/`, `*.gen.ts`, and lockfiles—are counted separately and disclosed on the Summary sheet.

This keeps generated output from distorting the headline totals. For example, one day in Mordad 1405 showed **+52,141 lines from two commits**, but the change came from a regenerated API client rather than a day's handwritten work.

### Span is not a timesheet

**Span (h)** measures the elapsed time between the first and last commit of a day. Two commits one minute apart therefore show `0`. It does not represent hours worked.

### Commit descriptions may be empty

**Commit Description** contains the commit body. Many commits contain only a subject line, so this field is often blank. It becomes useful when multi-line commit messages are used.

## Troubleshooting

<details>
<summary><strong>No commits found for this period</strong></summary>

The most common causes are the author filter and selected period. Try `--all-authors`, widen the range, or inspect the repository's oldest commit:

```bash
git log --format=%aI | tail -1
```

The displayed Git timestamp is Gregorian.

</details>

<details>
<summary><strong>Cannot write the workbook because it is open in Excel</strong></summary>

Close the workbook and generate it again, or provide another output path with `-o`.

</details>

<details>
<summary><strong>Range end precedes start</strong></summary>

The dates are reversed, or the end year contains a typo—for example, `1404` instead of `1405`.

</details>

<details>
<summary><strong>Path is not a Git repository</strong></summary>

Run the CLI from inside the repository, or select it with `--repo <path>`. In the desktop app, the project is skipped and the reason is shown after the run finishes.

</details>

<details>
<summary><strong>The app does not start or no window appears</strong></summary>

Run the following command in a terminal to see the underlying error:

```bash
python gui.py
```

If Python reports that the `tkinter` module is missing, reinstall Python with **tcl/tk and IDLE** enabled.

</details>

<details>
<summary><strong>A project is skipped</strong></summary>

The project either has no commits in the selected period, or the author filter removed every matching commit. Enable **Everyone** to check.

</details>

<details>
<summary><strong>Reset the desktop app</strong></summary>

Delete `gitreport-config.json`. A corrupt configuration file is ignored automatically instead of crashing the application.

</details>

## Project structure

| File | Responsibility |
| --- | --- |
| `gui.py` | Tkinter desktop app; runs report generation on a worker thread |
| `main.py` | CLI parsing, validation, and wiring |
| `service.py` | Shared engine used by both front ends |
| `config.py` | Settings, portable paths, and `gitreport-config.json` |
| `build_exe.py` | Builds the portable single-file executable |
| `jalali.py` | Jalali parsing, conversion, and formatting |
| `gitlog.py` | Runs `git log` and parses commits and file statistics |
| `report.py` | Groups commits by day and computes totals |
| `excel.py` | Renders the workbook worksheets |

The desktop app and CLI both call `service.generate`, so reporting logic is not duplicated and fixes apply to both interfaces.

Reports are written to `temp/` when run from source, or `reports/` beside the executable. The required folder is created automatically.

## Credits

Git Activity Report — **© M4hd1**

The attribution appears in the application footer, the workbook's Summary sheet, and the workbook file properties.

---

<div align="center">

[![Download for Windows](https://img.shields.io/badge/Download_for_Windows-v1.0.0-0078D4?style=for-the-badge&logo=windows11&logoColor=white)](https://github.com/Mahdi-Hazrati/Git-Activity-Report/releases/download/v1.0.0/GitActivityReport.exe)

**Ready to generate your first report? Download the portable app and get started.**

</div>

"""Build a single-file portable executable.

    python build_exe.py

Produces ``dist/GitActivityReport.exe`` - one file, no Python needed on the
target machine. git must still be installed there, since the report is read
from real repositories.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
APP_NAME = "GitActivityReport"

# Hidden imports: modules reached only via import inside functions, which
# PyInstaller's static analysis can miss.
HIDDEN = ["jdatetime", "jalali_core", "openpyxl", "et_xmlfile"]


def clean() -> None:
    """Remove build output, preserving anything the user owns in dist/.

    dist/ accumulates the running app's config and reports; wiping it would
    throw away a user's settings on every rebuild.
    """
    shutil.rmtree(HERE / "build", ignore_errors=True)
    shutil.rmtree(HERE / "__pycache__", ignore_errors=True)

    exe = HERE / "dist" / f"{APP_NAME}.exe"
    if exe.exists():
        try:
            exe.unlink()
        except PermissionError:
            print(f"Close {APP_NAME}.exe first - it is running.", file=sys.stderr)
            raise SystemExit(1)

    spec = HERE / f"{APP_NAME}.spec"
    if spec.exists():
        spec.unlink()


def build() -> int:
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--windowed",  # no console window
        f"--name={APP_NAME}",
        "--noconfirm",
        "--clean",
        f"--distpath={HERE / 'dist'}",
        f"--workpath={HERE / 'build'}",
        f"--specpath={HERE}",
    ]
    for module in HIDDEN:
        command += ["--hidden-import", module]

    icon = HERE / "icon.ico"
    if icon.exists():
        command.append(f"--icon={icon}")

    command.append(str(HERE / "gui.py"))

    print("Building... this takes a minute.\n")
    result = subprocess.run(command, cwd=HERE)
    if result.returncode != 0:
        print("\nBuild failed.", file=sys.stderr)
        return result.returncode

    exe = HERE / "dist" / f"{APP_NAME}.exe"
    size = exe.stat().st_size / (1024 * 1024) if exe.exists() else 0
    print(f"\nBuilt {exe}  ({size:.1f} MB)")
    print("Copy that single file anywhere - it needs no Python install.")
    return 0


if __name__ == "__main__":
    clean()
    raise SystemExit(build())

@echo off
rem Launch the report GUI without leaving a console window behind.
cd /d "%~dp0"
start "" pythonw gui.py

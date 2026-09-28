@echo off
REM Convenience launcher: starts backend + frontend together.
cd /d "%~dp0"
python scripts\run_dev.py

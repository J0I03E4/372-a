@echo off
REM Wrapper for the hourly Scheduled Task -- ensures we run from this folder
REM (schtasks doesn't let you set a working dir directly on the command line)
REM using the project's own dedicated venv rather than Code Puppy's install.
cd /d "%~dp0"
".venv\Scripts\python.exe" refresh_and_publish.py --push

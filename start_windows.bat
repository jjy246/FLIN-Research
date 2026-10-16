@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=py -3.12"
%PYTHON% --version >nul 2>&1
if errorlevel 1 set "PYTHON=python"
%PYTHON% --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.12 is required. Install it from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
  echo Creating FLIN virtual environment...
  %PYTHON% -m venv .venv || goto error
)
echo Installing or updating Python packages...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto error
".venv\Scripts\python.exe" flin_desktop.py
if errorlevel 1 goto error
exit /b 0
:error
  echo FLIN could not start. Read docs\TROUBLESHOOTING.md
  pause
  exit /b 1

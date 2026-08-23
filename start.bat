@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo [1/4] Checking Python ...
set "PYBIN="

rem ---------- detection order ----------
rem 1) env var PAPERSUMMAR_PYTHON
if defined PAPERSUMMAR_PYTHON set "PYBIN=%PAPERSUMMAR_PYTHON%"

rem 2) Windows py launcher, then python in PATH.
rem    A Microsoft Store python stub prints nothing, so it is skipped automatically.
if not defined PYBIN for /f "delims=" %%i in ('py -3 -c "import sys; print(sys.executable)" 2^>nul') do if not defined PYBIN set "PYBIN=%%i"
if not defined PYBIN for /f "delims=" %%i in ('python -c "import sys,venv; print(sys.executable)" 2^>nul') do if not defined PYBIN set "PYBIN=%%i"

rem 3) common conda install locations
if not defined PYBIN if exist "%USERPROFILE%\anaconda3\python.exe" set "PYBIN=%USERPROFILE%\anaconda3\python.exe"
if not defined PYBIN if exist "%USERPROFILE%\miniconda3\python.exe" set "PYBIN=%USERPROFILE%\miniconda3\python.exe"
if not defined PYBIN if exist "C:\ProgramData\anaconda3\python.exe" set "PYBIN=C:\ProgramData\anaconda3\python.exe"
if not defined PYBIN if exist "C:\ProgramData\miniconda3\python.exe" set "PYBIN=C:\ProgramData\miniconda3\python.exe"

if not defined PYBIN (
    echo [ERROR] No working Python found.
    echo         The "python" in PATH may be the Microsoft Store stub.
    echo         Install Python 3.11+ from https://www.python.org/downloads/ ^(check Add to PATH^),
    echo         or set environment variable PAPERSUMMAR_PYTHON to your python.exe.
    pause
    exit /b 1
)
echo        Using Python: %PYBIN%

echo [2/4] Running setup and launch ...
"%PYBIN%" "%~dp0scripts\launch.py"
if errorlevel 1 (
    echo [ERROR] Setup failed. See messages above.
    pause
    exit /b 1
)

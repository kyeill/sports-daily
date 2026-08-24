@echo off
REM Builds output\today.html, invoked by the "sports daily" scheduled task.
REM Safe to double-click to test. Output is appended to run.log.

setlocal
set "PY=C:\Users\kyleh\AppData\Local\Programs\Python\Python312-arm64\python.exe"
set "PROJ=%~dp0"
set "PYTHONIOENCODING=utf-8"

cd /d "%PROJ%"
echo. >> "%PROJ%run.log"
echo ===== %DATE% %TIME% ===== >> "%PROJ%run.log"

"%PY%" sports_daily.py >> "%PROJ%run.log" 2>&1
echo exit code: %ERRORLEVEL% >> "%PROJ%run.log"
endlocal

@echo off
setlocal EnableExtensions

REM Script location: warranty\scripts
set "ROOT=%~dp0.."
set "TARGET=%ROOT%\data\raw data"

REM Normalize path
for %%P in ("%TARGET%") do set "TARGET=%%~fP"

REM Safety check
if not exist "%TARGET%" (
  echo ERROR: Target folder not found:
  echo   %TARGET%
  pause
  exit /b 1
)

echo =========================================
echo Removing .DS_Store files from:
echo   %TARGET%
echo =========================================
echo.

REM Recursively delete .DS_Store files
for /r "%TARGET%" %%F in (.DS_Store) do (
  echo Deleting %%F
  del "%%F"
)

echo.
echo Done.
pause

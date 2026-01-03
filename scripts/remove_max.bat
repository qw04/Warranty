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
echo Removing __MACOSX folders from:
echo   %TARGET%
echo =========================================
echo.

REM Recursively find and remove __MACOSX folders
for /d /r "%TARGET%" %%D in (__MACOSX) do (
  echo Removing %%D
  rmdir /s /q "%%D"
)

echo.
echo Done.
pause

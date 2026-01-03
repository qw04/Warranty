@echo off
setlocal EnableExtensions

REM Script lives in warranty\scripts
set "ROOT=%~dp0.."
set "RAW=%ROOT%\data\raw_data"

REM Normalize path
for %%P in ("%RAW%") do set "RAW=%%~fP"

REM Safety check
if not exist "%RAW%" (
  echo raw_data folder does not exist:
  echo   %RAW%
  echo Nothing to clean.
  pause
  exit /b 0
)

echo =========================================
echo Deleting all .zip files in raw_data
echo =========================================

for %%Z in ("%RAW%\*.zip") do (
  echo Deleting %%~nxZ
  del "%%Z"
)

echo.
echo =========================================
echo Deleting raw_data folder
echo =========================================

rmdir /s /q "%RAW%"
if errorlevel 1 (
  echo ERROR: Failed to delete raw_data
  pause
  exit /b 1
)

echo.
echo Cleanup complete.
pause

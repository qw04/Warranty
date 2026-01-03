@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM =====================================================
REM Paths (script is in warranty\scripts)
REM =====================================================
set "ROOT=%~dp0.."
set "RAW=%ROOT%\data\raw_data"
set "FINAL=%ROOT%\data\raw data"

REM Normalize paths
for %%P in ("%RAW%") do set "RAW=%%~fP"
for %%P in ("%FINAL%") do set "FINAL=%%~fP"

REM -----------------------------------------------------
REM Safety checks
REM -----------------------------------------------------
if not exist "%RAW%" (
  echo ERROR: raw_data not found:
  echo   %RAW%
  pause
  exit /b 1
)

if not exist "%FINAL%" (
  mkdir "%FINAL%"
)

echo =========================================
echo STEP 1: Unzipping all ZIP files in raw_data
echo =========================================

for %%Z in ("%RAW%\*.zip") do (
  echo Unzipping %%~nxZ
  powershell -NoProfile -Command ^
    "Expand-Archive -Force '%%Z' '%RAW%\%%~nZ'"
)

echo.
echo =========================================
echo STEP 2: Flatten data_Q*\data_Q* folders
echo =========================================

for /d %%O in ("%RAW%\data_Q*") do (

  set "HASINNER=0"
  for /d %%X in ("%%O\data_Q*") do set "HASINNER=1"

  if "!HASINNER!"=="1" (
    echo Processing wrapper: %%~nxO

    set "WRAP=%%~nxO__wrapper__!random!"
    ren "%%O" "!WRAP!"

    set "WRAPPED=%RAW%\!WRAP!"

    for /d %%I in ("!WRAPPED!\data_Q*") do (
      echo   Unwrapping %%~nxI
      if exist "%RAW%\%%~nxI" (
        rmdir /s /q "%RAW%\%%~nxI"
      )
      move "%%I" "%RAW%\" >nul
    )

    rmdir /s /q "!WRAPPED!"
  )
)

echo.
echo =========================================
echo STEP 3: Move folders into "raw data"
echo =========================================

for /d %%D in ("%RAW%\*") do (
  echo Moving %%~nxD
  if exist "%FINAL%\%%~nxD" (
    rmdir /s /q "%FINAL%\%%~nxD"
  )
  move "%%D" "%FINAL%\" >nul
)

echo.
echo =========================================
echo DONE
echo =========================================
pause

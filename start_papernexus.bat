@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=C:\Users\19653\miniforge3\envs\papernexus\python.exe"
set "HOST=127.0.0.1"
set "PORT=8000"

if not exist "%PYTHON%" (
  echo PaperNexus startup failed.
  echo Python interpreter not found at:
  echo   %PYTHON%
  pause
  exit /b 1
)

cd /d "%ROOT%"

set "NOUGAT_ENABLED=true"
set "NOUGAT_COMMAND=C:\Users\19653\miniforge3\envs\papernexus\Scripts\nougat.exe"
set "NOUGAT_TIMEOUT_SEC=1800"
set "NOUGAT_TMP_DIR=.nougat_tmp\runs"
set "NOUGAT_CACHE_DIR=.nougat_tmp\cache"
set "NOUGAT_NLTK_DATA_DIR=.nougat_tmp\nltk_data"
set "NOUGAT_MAX_PAGES=12"
set "NO_ALBUMENTATIONS_UPDATE=1"

echo Starting PaperNexus on http://%HOST%:%PORT%/
start "PaperNexus Server" cmd /k ""%PYTHON%" -m uvicorn backend.main:app --host %HOST% --port %PORT% --reload"
timeout /t 4 /nobreak >nul
start "" "http://%HOST%:%PORT%/"

exit /b 0

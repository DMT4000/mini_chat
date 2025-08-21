@echo off
REM Windows batch file for Mini Chat
REM Provides shortcuts for running the app and tests

if "%1"=="" goto help
if "%1"=="help" goto help
if "%1"=="start" goto start:stable
if "%1"=="start:stable" goto start:stable
if "%1"=="start:exp" goto start:exp
if "%1"=="smoke" goto smoke
if "%1"=="smoke:exp" goto smoke:exp
if "%1"=="install" goto install
goto help

:start:stable
echo 🟢 Starting Mini Chat in STABLE mode...
set EXPERIMENTAL=0
python -m uvicorn src.api:app --reload --port 8000
goto end

:start:exp
echo 🔴 Starting Mini Chat in EXPERIMENTAL mode...
set EXPERIMENTAL=1
python -m uvicorn src.api:app --reload --port 8000
goto end

:smoke
echo 🧪 Running smoke test against stable app...
powershell -ExecutionPolicy Bypass -File scripts\smoke.ps1
goto end

:smoke:exp
echo 🧪 Running smoke test against experimental app...
set EXPERIMENTAL=1
powershell -ExecutionPolicy Bypass -File scripts\smoke.ps1
goto end

:install
echo 📦 Installing dependencies...
pip install -r requirements.txt
goto end

:help
echo Mini Chat - Available commands:
echo.
echo App Management:
echo   start:stable    Start app in stable mode (default)
echo   start:exp       Start app in experimental mode
echo   install         Install dependencies
echo.
echo Testing:
echo   smoke           Run smoke test against stable app
echo   smoke:exp       Run smoke test against experimental app
echo.
echo Examples:
echo   run.bat start:stable
echo   run.bat start:exp
echo   run.bat smoke
echo   run.bat smoke:exp
echo.
goto end

:end

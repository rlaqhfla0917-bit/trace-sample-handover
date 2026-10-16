@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv ( py -3 -m venv .venv )
if not exist .venv\Scripts\python.exe (
  echo Python 3.10 or newer is required. Install it from python.org.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check your internet connection.
  pause
  exit /b 1
)
start "" /b cmd /c "timeout /t 3 >nul & start http://127.0.0.1:8502"
.venv\Scripts\python.exe app.py
pause

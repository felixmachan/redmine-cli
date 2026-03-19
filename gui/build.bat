@echo off
setlocal
cd /d "%~dp0"

if not exist venv\Scripts\python.exe (
  echo [ERROR] venv nincs meg. Hozd letre: python -m venv venv
  exit /b 1
)

venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m pip install pyinstaller
venv\Scripts\pyinstaller.exe --noconfirm --clean --onedir --name redmine-cli main.py

if exist ..\.env copy /Y ..\.env dist\redmine-cli\.env >nul
copy /Y unfilled.xlsx dist\redmine-cli\unfilled.xlsx >nul

echo Build kesz: dist\redmine-cli\redmine-cli.exe

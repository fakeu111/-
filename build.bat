@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --windowed --name Ñ§Ï°×ÀÃæ --icon resources/app.ico --add-data "resources;resources" --add-data "app/ui/style.qss;app/ui" --collect-data docx --collect-submodules docx app/main.py
echo BUILD_EXIT=%ERRORLEVEL%

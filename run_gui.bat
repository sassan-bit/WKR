@echo off
chcp 65001 >nul
if not exist ".venv\Scripts\python.exe" (
    echo Виртуальное окружение не найдено. Запустите setup_and_run.bat
    pause
    exit /b 1
)
.venv\Scripts\python.exe src/gui.py

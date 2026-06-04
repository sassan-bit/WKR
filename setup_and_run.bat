@echo off
chcp 65001 >nul
echo ============================================================
echo   Антивирусная система — установка и запуск
echo ============================================================
echo.

:: Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python не найден. Устанавливаем автоматически...
    echo.
    winget install --id Python.Python.3.11 --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
    if errorlevel 1 (
        echo [ОШИБКА] Автоустановка не удалась.
        echo Скачайте Python 3.10+ вручную: https://python.org
        echo При установке отметьте "Add Python to PATH".
        pause
        exit /b 1
    )
    echo [OK] Python установлен
    :: Обновляем PATH в текущей сессии
    for /f "tokens=*" %%i in ('powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable(\"PATH\",\"Machine\") + \";\" + [Environment]::GetEnvironmentVariable(\"PATH\",\"User\")"') do set "PATH=%%i"
)

for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYVER=%%v
echo [OK] Python %PYVER% найден

:: Создание виртуального окружения если не существует
if not exist ".venv\Scripts\python.exe" (
    echo.
    echo [*] Создание виртуального окружения...
    python -m venv .venv
    if errorlevel 1 (
        echo [ОШИБКА] Не удалось создать виртуальное окружение
        pause
        exit /b 1
    )
    echo [OK] Виртуальное окружение создано
) else (
    echo [OK] Виртуальное окружение уже существует
)

:: Установка зависимостей
echo.
echo [*] Установка зависимостей (может занять несколько минут)...
.venv\Scripts\pip install -r requirements.txt --quiet --disable-pip-version-check
if errorlevel 1 (
    echo [ОШИБКА] Ошибка при установке зависимостей
    pause
    exit /b 1
)
echo [OK] Зависимости установлены

:: Проверка наличия модели
echo.
if not exist "model\malware_detector.model" (
    echo [!] Модель не найдена — запуск обучения...
    echo     Это займёт несколько минут.
    echo.
    .venv\Scripts\python src\train_model.py ^
        --malware-dir data\malware ^
        --benign-dir data\benign ^
        --cv-folds 0
    if errorlevel 1 (
        echo [ОШИБКА] Ошибка при обучении модели
        pause
        exit /b 1
    )
    echo [OK] Модель обучена
) else (
    echo [OK] Модель найдена
)

:: Запуск GUI
echo.
echo ============================================================
echo   Запуск приложения...
echo ============================================================
.venv\Scripts\python src\gui.py

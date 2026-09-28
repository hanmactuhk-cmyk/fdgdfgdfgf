@echo off
python -m pip install -r requirements.txt
if errorlevel 1 pause & exit /b 1
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --clean --windowed --name G-Labs-Flow-Video --collect-all PySide6 desktop\main.py
if errorlevel 1 pause & exit /b 1
echo.
echo EXE: dist\G-Labs-Flow-Video.exe
pause

@echo off
setlocal
python -m pip install --upgrade pip
python -m pip install pyinstaller
pyinstaller --noconfirm --clean --onefile --windowed --name RetailWindowsV2 app.py
echo.
echo EXE-ul este in dist\RetailWindowsV2.exe
pause

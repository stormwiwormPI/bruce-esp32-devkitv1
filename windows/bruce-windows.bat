@echo off
setlocal

title Bruce - ESP32 DevKit V1 (Windows)
cd /d "%~dp0.."

set "WEBPORT=8080"

echo.
echo   ==========================================================
echo     Bruce  -  ESP32 DevKit V1 (Windows)
echo   ==========================================================
echo.
echo   Bruce renders its menu in software and your browser shows it.
echo   Open the "Navigator" tab for the menu and nav buttons.
echo.
echo   ==========================================================
echo.

REM ---------- Python ----------------------------------------------------
where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python was not found.
    echo      Install it from https://www.python.org/downloads/
    echo      and tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

python -c "import serial" >nul 2>&1
if errorlevel 1 (
    echo  Installing pyserial ...
    python -m pip install --quiet pyserial
)

REM ---------- Free the port ---------------------------------------------
echo  Releasing the serial port ...
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'python*' -and $_.CommandLine -like '*bruce_cable_ui*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }" >nul 2>&1
timeout /t 2 /nobreak >nul

REM ---------- Find the board --------------------------------------------
echo  Looking for the board ...
set "PORT="
for /f "usebackq delims=" %%p in (`python -c "from serial.tools import list_ports; print(next((p.device for p in list_ports.comports() if 'VID:PID=' in (p.hwid or '').upper()), 'NONE'))"`) do set "PORT=%%p"

if not defined PORT goto :noboard
if "%PORT%"=="NONE" goto :noboard
echo  [OK] Board found on %PORT%
echo.

REM ---------- Start the interface ---------------------------------------
echo  Starting interface on http://127.0.0.1:%WEBPORT%/ ...
echo.
python bruce_cable_ui.py --port %PORT% --http %WEBPORT%
set "EXITCODE=%errorlevel%"
if %EXITCODE% neq 0 (
    echo.
    echo  [!] Server stopped with exit code %EXITCODE%
    echo.
    pause
)
exit /b %EXITCODE%

:noboard
echo  [X] ESP32 board not detected.
echo.
echo      1. Connect the board via a micro-USB DATA cable (not charge-only).
echo      2. If Device Manager shows an unknown device or CP2102/CH340 with
echo         a yellow exclamation mark, install the driver:
echo           CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
echo           CH340:  http://www.wch-ic.com/downloads/CH341SER_EXE.html
echo      3. Run this script again.
echo.
pause
exit /b 1

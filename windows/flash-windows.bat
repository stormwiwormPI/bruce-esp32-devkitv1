@echo off
REM ==============================================================
REM  Flash the Bruce firmware to the ESP32 DevKit V1 (Windows)
REM ==============================================================

title Flash Bruce firmware (Windows)
cd /d "%~dp0.."

set "IMAGE=bruce-devkitv1-port\Bruce-esp32-devkitv1.bin"

echo.
echo   ==========================================================
echo     Flash Bruce firmware to the ESP32 DevKit V1 (Windows)
echo   ==========================================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python was not found.
    echo      Install it from https://www.python.org/downloads/
    echo      and tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

python -c "import esptool" >nul 2>&1
if errorlevel 1 (
    echo  Installing esptool ...
    python -m pip install --quiet esptool
)

if not exist "%IMAGE%" (
    echo  [X] Firmware image not found:
    echo      %IMAGE%
    echo.
    pause
    exit /b 1
)

echo  Looking for the board ...
set "PORT="
for /f "usebackq delims=" %%p in (`python -c "from serial.tools import list_ports; print(next((p.device for p in list_ports.comports() if 'VID:PID=' in (p.hwid or '').upper()), 'NONE'))"`) do set "PORT=%%p"

if not defined PORT goto :noboard
if "%PORT%"=="NONE" goto :noboard

echo  [OK] Board found on %PORT%
echo.
echo  Close any serial monitor or terminal using that port.
timeout /t 3 /nobreak >nul
echo.
echo  Flashing - this takes about a minute. Do not unplug the board.
echo.

python -m esptool --chip esp32 --port %PORT% --baud 460800 ^
    write-flash 0x0 "%IMAGE%"

if errorlevel 1 (
    echo.
    echo  [X] Flashing failed.
    echo      If the port was busy, close the other program and retry.
    echo      If it still fails, hold BOOT, tap RESET, release BOOT, retry.
    echo.
    pause
    exit /b 1
)

echo.
echo  ==========================================================
echo    Done. The board has rebooted into Bruce firmware.
echo.
echo    Now run  bruce-windows.bat  to open the interface.
echo  ==========================================================
echo.
pause
exit /b 0

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

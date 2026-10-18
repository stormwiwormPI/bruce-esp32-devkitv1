@echo off
setlocal enabledelayedexpansion

title Build Bruce Firmware - ESP32 DevKit V1
cd /d "%~dp0"

echo.
echo   ==========================================================
echo     Build Bruce Firmware for ESP32 DevKit V1
echo   ==========================================================
echo.

REM 1. Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo  [X] Python was not found. Please install Python 3.10+
    echo      and tick "Add python.exe to PATH".
    echo.
    pause
    exit /b 1
)

REM 2. Check PlatformIO
python -m platformio --version >nul 2>&1
if errorlevel 1 (
    echo  PlatformIO not detected. Installing platformio via pip ...
    python -m pip install --upgrade platformio
    if errorlevel 1 (
        echo  [X] Failed to install PlatformIO.
        pause
        exit /b 1
    )
)

REM 3. Restore libnet80211.a if shipped as .old by upstream framework package
python -c "
import os, glob, shutil
pio_dir = os.path.expanduser('~/.platformio/packages')
for old_lib in glob.glob(os.path.join(pio_dir, 'framework-arduinoespressif32-libs*', '**', 'libnet80211.a.old'), recursive=True):
    target = old_lib[:-4]
    if not os.path.exists(target):
        try:
            shutil.copy2(old_lib, target)
            print(f'Restored: {target}')
        except Exception:
            pass
" >nul 2>&1

echo  Starting compilation for esp32-devkitv1 ...
echo  This takes a few minutes on the first build. Please wait.
echo.

python -m platformio run -e esp32-devkitv1
if errorlevel 1 (
    echo.
    echo  [X] Compilation failed. Review the errors above.
    echo.
    pause
    exit /b 1
)

echo.
echo  Checking for merged binary ...
set "MERGED_BIN=Bruce-esp32-devkitv1.bin"
set "TARGET_DIR=..\bruce-devkitv1-port"
set "TARGET_BIN=%TARGET_DIR%\Bruce-esp32-devkitv1.bin"

if not exist "%MERGED_BIN%" (
    if exist ".pio\build\esp32-devkitv1\firmware.factory.bin" (
        copy /y ".pio\build\esp32-devkitv1\firmware.factory.bin" "%MERGED_BIN%" >nul
    )
)

if exist "%MERGED_BIN%" (
    if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"
    copy /y "%MERGED_BIN%" "%TARGET_BIN%" >nul
    echo  [OK] Successfully built and updated:
    echo       %TARGET_BIN%
) else (
    echo  [!] Firmware built, but combined 0x0 binary not found at %MERGED_BIN%.
)

echo.
echo  ==========================================================
echo    Build finished successfully!
echo    You can now flash the firmware using flash.bat
echo  ==========================================================
echo.
pause
exit /b 0

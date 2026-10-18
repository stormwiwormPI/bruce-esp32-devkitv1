#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  =========================================================="
echo "    Build Bruce Firmware for ESP32 DevKit V1"
echo "  =========================================================="
echo ""

if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "  [X] Python 3 is required. Please install python3 & python3-pip."
    exit 1
fi

if ! $PYTHON -m platformio --version >/dev/null 2>&1; then
    echo "  Installing PlatformIO CLI..."
    $PYTHON -m pip install --quiet platformio 2>/dev/null || \
    $PYTHON -m pip install --quiet --break-system-packages platformio 2>/dev/null || \
    pip3 install --user platformio 2>/dev/null
fi

# Restore libnet80211.a if shipped as .old by upstream framework package
$PYTHON -c "
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
" >/dev/null 2>&1 || true

echo "  Starting compilation for esp32-devkitv1..."
echo "  This takes a few minutes on the first build. Please wait."
echo ""

$PYTHON -m platformio run -e esp32-devkitv1

MERGED_BIN="Bruce-esp32-devkitv1.bin"
TARGET_DIR="../bruce-devkitv1-port"
TARGET_BIN="$TARGET_DIR/Bruce-esp32-devkitv1.bin"

if [ ! -f "$MERGED_BIN" ] && [ -f ".pio/build/esp32-devkitv1/firmware.factory.bin" ]; then
    cp ".pio/build/esp32-devkitv1/firmware.factory.bin" "$MERGED_BIN"
fi

if [ -f "$MERGED_BIN" ]; then
    mkdir -p "$TARGET_DIR"
    cp "$MERGED_BIN" "$TARGET_BIN"
    echo ""
    echo "  [OK] Successfully built and updated: $TARGET_BIN"
fi

echo ""
echo "  =========================================================="
echo "    Build finished successfully!"
echo "    You can now flash the firmware using flash.sh or flash.bat"
echo "  =========================================================="
echo ""

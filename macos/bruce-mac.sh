#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

WEBPORT=8080

echo ""
echo "  =========================================================="
echo "    Bruce  -  ESP32 DevKit V1 (macOS)"
echo "  =========================================================="
echo ""
echo "  Bruce renders its menu in software and your browser shows it."
echo "  Open the 'Navigator' tab for the menu and nav buttons."
echo ""
echo "  =========================================================="
echo ""

# 1. Python Check
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "  [X] Python 3 was not found."
    echo "      Install Python 3 from https://www.python.org/downloads/ or via Homebrew: brew install python"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# 2. PySerial Check
if ! $PYTHON -c "import serial" >/dev/null 2>&1; then
    echo "  Installing pyserial ..."
    $PYTHON -m pip install --quiet pyserial 2>/dev/null || \
    $PYTHON -m pip install --quiet --break-system-packages pyserial 2>/dev/null || \
    pip3 install --user pyserial 2>/dev/null || true
fi

# 3. Release any previous instance
pkill -f "bruce_cable_ui.py" 2>/dev/null || true
sleep 1

# 4. Detect Board Port
echo "  Looking for the board ..."
PORT=$($PYTHON -c "
import sys
try:
    from serial.tools import list_ports
    for p in list_ports.comports():
        h = (p.hwid or '').upper()
        d = (p.description or '').lower()
        if 'VID:PID=' in h or any(x in d for x in ('cp210','ch34','ftdi','uart','usb','serial')):
            print(p.device); sys.exit(0)
    for p in list_ports.comports():
        if '/dev/cu.usb' in p.device or '/dev/cu.SLAB' in p.device or '/dev/cu.wch' in p.device:
            print(p.device); sys.exit(0)
except Exception:
    pass
print('NONE')
")

if [ "$PORT" = "NONE" ] || [ -z "$PORT" ]; then
    for dev in /dev/cu.usbserial* /dev/cu.SLAB_USBtoUART* /dev/cu.wchusbserial* /dev/cu.usbmodem*; do
        if [ -e "$dev" ]; then
            PORT="$dev"
            break
        fi
    done
fi

if [ -z "$PORT" ] || [ "$PORT" = "NONE" ] || [ ! -e "$PORT" ]; then
    echo "  [X] ESP32 board not detected."
    echo ""
    echo "      1. Connect the board via a micro-USB DATA cable (not charge-only)."
    echo "      2. If using CP2102 or CH340, install the macOS driver:"
    echo "           CP210x: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers"
    echo "           CH34x:  https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver"
    echo "      3. Run this script again."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "  [OK] Board found on $PORT"
echo ""
echo "  Starting interface on http://127.0.0.1:$WEBPORT/ ..."
echo ""

exec $PYTHON "$ROOT_DIR/bruce_cable_ui.py" --port "$PORT" --http "$WEBPORT"

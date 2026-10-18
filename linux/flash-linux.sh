#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

IMAGE="$ROOT_DIR/bruce-devkitv1-port/Bruce-esp32-devkitv1.bin"

echo ""
echo "  =========================================================="
echo "    Flash Bruce firmware to ESP32 DevKit V1 (Linux)"
echo "  =========================================================="
echo ""

# 1. Python Check
if command -v python3 >/dev/null 2>&1; then
    PYTHON="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON="python"
else
    echo "  [X] Python 3 was not found."
    echo "      Install Python 3 with: sudo apt install python3 python3-pip"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# 2. esptool Check
if ! $PYTHON -c "import esptool" >/dev/null 2>&1; then
    echo "  Installing esptool ..."
    $PYTHON -m pip install --quiet esptool 2>/dev/null || \
    $PYTHON -m pip install --quiet --break-system-packages esptool 2>/dev/null || \
    pip3 install --user esptool 2>/dev/null || true
fi

if [ ! -f "$IMAGE" ]; then
    echo "  [X] Firmware image not found: $IMAGE"
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

# 3. Detect Board Port
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
        if '/dev/ttyUSB' in p.device or '/dev/ttyACM' in p.device:
            print(p.device); sys.exit(0)
except Exception:
    pass
print('NONE')
")

if [ "$PORT" = "NONE" ] || [ -z "$PORT" ]; then
    for dev in /dev/ttyUSB* /dev/ttyACM*; do
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
    echo "      2. Check if the device shows up in: dmesg | tail"
    echo "      3. Run this script again."
    echo ""
    read -p "Press Enter to exit..."
    exit 1
fi

echo "  [OK] Board found on $PORT"
echo ""

# Check user permissions on the serial port
if [ ! -r "$PORT" ] || [ ! -w "$PORT" ]; then
    echo "  [!] Permission warning: Current user may lack write access to $PORT"
    echo "      Run: sudo usermod -a -G dialout $USER"
    echo "      (Or sudo usermod -a -G uucp $USER on Arch Linux)"
    echo "      Then log out and log back in, or run this script with sudo."
    echo ""
fi

echo "  Flashing - this takes about a minute. Do not unplug the board."
echo ""

$PYTHON -m esptool --chip esp32 --port "$PORT" --baud 460800 write-flash 0x0 "$IMAGE"

echo ""
echo "  =========================================================="
echo "    Done. The board has rebooted into Bruce firmware."
echo ""
echo "    Now run  ./linux/bruce-linux.sh  to open the interface."
echo "  =========================================================="
echo ""

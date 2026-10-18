# Bruce Firmware Source Code (ESP32 DevKit V1 Port)

This folder contains the complete, modified source code for running **Bruce** on the bare **ESP32 DevKit V1** (ESP32-D0WD-V3, WROOM-32, 4MB Flash, No PSRAM, No physical display).

---

## What Was Added / Fixed for DevKit V1

1. **Virtual Display Architecture (`-DVIRTUAL_DISPLAY=1`)**:
   - `include/tftLogger.h`: Compiles in the software vector renderer (`SerialDisplayClass`) instead of driving a physical SPI panel, so no GPIO SPI signals are wasted on an absent display.
   - Outputs binary draw commands (`getBinLog()`) streamed over serial to the PC WebUI Navigator.
2. **4MB Flash Partition Scheme (`custom_4Mb_full.csv`)**:
   - Allocates 3.52 MB (0x380000) for firmware and 192 KB for LittleFS, fitting the entire feature-rich Bruce suite within standard 4MB flash.
3. **BLE Media Commands Fixes**:
   - Out-of-bounds bug fixed in `lib/Bad_Usb_Lib/BleKeyboard.cpp:202`.
   - Uses real chip hardware Bluetooth MAC to prevent ghost auto-pairing.
   - Prevents menu exit when clicking volume or media keys.
4. **Submenu Persistence**:
   - Wrapped submenus (WiFi, Bluetooth, Files, RF, IR, RFID, Others) in persistent loops so finishing an action keeps you inside that category submenu instead of dumping you to the main carousel.
5. **Onboard Status LED**:
   - `src/core/status_led.cpp`: Drives GPIO 2 with a gentle heartbeat pulse (normal operation) and a 10Hz rapid strobe (during attacks).
6. **Maximized WiFi Output Power**:
   - Automatically configures `19.5 dBm` (raw level 78) and disables modem sleep across all WiFi operations.
7. **Date/Time Sync Over Serial**:
   - Implemented `date set <epoch>` serial command to sync the board's internal RTC to the PC clock.
8. **Chunked Base64 File Writer**:
   - Implemented `writeb64 <path> <mode: w|a> <base64>` in `src/core/serial_commands/storage_commands.cpp` to enable uploading, editing, and deleting files via the WebUI over the USB cable.

---

## How to Build

### Prerequisites
- **Python 3.10+**
- **PlatformIO** (`pip install platformio`)

### Windows
Double-click `build-windows.bat` (or `build.bat`):
```bat
build-windows.bat
```

### Linux
Make executable and run:
```bash
chmod +x build-linux.sh
./build-linux.sh
```

### macOS
Make executable and run:
```bash
chmod +x build-mac.sh
./build-mac.sh
```

### Manual Command
```bash
python -m platformio run -e esp32-devkitv1
```

The build script will automatically compile, merge the bootloader, partitions, and firmware into a single binary image, and copy it to:
```
../bruce-devkitv1-port/Bruce-esp32-devkitv1.bin
```

---

## How to Flash

After building, flash the board from the root directory or OS folder:
- **Windows**: run `flash-windows.bat` (or `windows\flash-windows.bat`)
- **Linux**: run `./flash-linux.sh` (or `./linux/flash-linux.sh`)
- **macOS**: run `./flash-mac.sh` (or `./macos/flash-mac.sh`)

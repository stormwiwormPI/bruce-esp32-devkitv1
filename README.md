# Bruce on a bare ESP32 DevKit V1

Runs [Bruce](https://github.com/BruceDevices/firmware) on a cheap ESP32 DevKit V1 (ESP32-D0WD-V3, WROOM-32, 4 MB flash, no PSRAM, **no physical display**) and shows its full graphical interface on your PC over the USB cable on **Windows**, **Linux**, and **macOS**.

Upstream ships no build for this board. This project provides a custom board model, full virtual display firmware, host transport, and automated scripts for Windows, Linux, and macOS.

---

## Folder Structure

```
work/
├── windows/                    # Windows scripts
│   ├── bruce-windows.bat       # Launch WebUI server and open browser
│   └── flash-windows.bat       # Flash precompiled firmware to COM port
├── linux/                      # Linux scripts (auto-detects /dev/ttyUSB* or /dev/ttyACM*)
│   ├── bruce-linux.sh          # Launch WebUI server and open browser
│   └── flash-linux.sh          # Flash precompiled firmware
├── macos/                      # macOS scripts (auto-detects /dev/cu.usbserial*)
│   ├── bruce-mac.sh            # Launch WebUI server and open browser
│   └── flash-mac.sh            # Flash precompiled firmware
├── source/                     # Full firmware source code (build from scratch)
│   ├── boards/                 # Board definitions (including esp32-devkitv1)
│   ├── src/                    # Core Bruce C++ source code & patches
│   ├── include/                # Headers & virtual display drivers
│   ├── lib/                    # Libraries (TFT_eSPI_QRcode, Bad_Usb_Lib, etc.)
│   ├── build-windows.bat       # 1-click Windows firmware builder
│   ├── build-linux.sh          # 1-command Linux firmware builder
│   ├── build-mac.sh            # 1-command macOS firmware builder
│   └── README.md               # Source & compilation documentation
├── bruce-devkitv1-port/        # Pre-built combined 0x0 factory firmware binary
│   └── Bruce-esp32-devkitv1.bin
├── webui_files/                # Cached monochrome WebUI assets
├── bruce-windows.bat           # Root Windows launcher
├── flash-windows.bat           # Root Windows flasher
├── bruce-linux.sh              # Root Linux launcher
├── flash-linux.sh              # Root Linux flasher
├── bruce-mac.sh                # Root macOS launcher
├── flash-mac.sh                # Root macOS flasher
└── bruce_cable_ui.py           # Cross-platform WebUI cable transport server
```

---

## No Physical Display, by Design

**This project is virtual-screen only. It does not drive a real TFT panel.**

The board has no physical display soldered on, and nothing here drives SPI panel signals. Bruce renders its menu completely in software (`VIRTUAL_DISPLAY=1`), and the host transport streams real vector draw commands to your browser's **Navigator** tab.

The board definition defines **no** display pins (`TFT_CS`, `TFT_DC`, `TFT_RST`, `TFT_MOSI`, `TFT_SCLK`, `TFT_BL`), saving GPIOs, power, and avoiding dead SPI bus waits.

---

## Quick Start

### 1. Get the Repository

Clone this project to your PC (or click **Fork** at the top right of this GitHub page and clone your personal fork):

```bash
# Clone directly:
git clone https://github.com/stormwiwormPI/bruce-esp32-devkitv1.git
cd bruce-esp32-devkitv1

# Or clone your personal fork to work from there:
git clone https://github.com/<your-username>/bruce-esp32-devkitv1.git
cd bruce-esp32-devkitv1
```

### 2. Connect Your Board

Connect your ESP32 DevKit V1 using a micro-USB **data** cable.

> [!TIP]
> **Board Not Recognized or Missing Serial Port?**
> If your PC or the script does not detect the board (e.g. Device Manager shows an unknown device or yellow exclamation mark, or the flash script reports `ESP32 board not detected`), you need the USB-to-UART bridge driver for your board:
> - **CP2102 / CP2104 Driver (Silicon Labs)**: [Download from Silicon Labs](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
> - **CH340 / CH341 Driver (WCH)**: [Download for Windows (EXE)](https://www.wch-ic.com/downloads/CH341SER_EXE.html) | [Download for macOS](https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver) | [SparkFun CH340 Guide](https://learn.sparkfun.com/tutorials/how-to-install-ch340-drivers/all)
> - **FTDI VCP Driver**: [Download from FTDI](https://ftdichip.com/drivers/vcp-drivers/)
>
> *Note: Make sure your cable is a true **data transfer cable**, not a charge-only power cable.*

### 3. Launch for Your Operating System

#### Windows
```cmd
1. Double-click  flash-windows.bat      (write firmware to board - once)
2. Double-click  bruce-windows.bat      (launch WebUI and open browser)
```
*(Or use `windows\flash-windows.bat` and `windows\bruce-windows.bat`)*

#### Linux
```bash
1. chmod +x flash-linux.sh bruce-linux.sh
2. ./flash-linux.sh                     (write firmware to board - once)
3. ./bruce-linux.sh                     (launch WebUI and open browser)
```
*(Or use `./linux/flash-linux.sh` and `./linux/bruce-linux.sh`)*

> [!NOTE]
> If you encounter a serial permission error on Linux, add your user to the `dialout` group:
> `sudo usermod -a -G dialout $USER` (or `sudo usermod -a -G uucp $USER` on Arch), then log out and back in.

#### macOS
```bash
1. chmod +x flash-mac.sh bruce-mac.sh
2. ./flash-mac.sh                       (write firmware to board - once)
3. ./bruce-mac.sh                       (launch WebUI and open browser)
```
*(Or use `./macos/flash-mac.sh` and `./macos/bruce-mac.sh`)*

---

## Using the Interface

Once `bruce.bat` or `bruce.sh` runs, it hosts the local interface at `http://127.0.0.1:8080/` and opens your browser.

| Tab | What it does |
|---|---|
| **Navigator** | The virtual display canvas. Shows genuine firmware draw commands. Use the on-screen D-pad or keyboard (Arrows, Enter, Backspace) to navigate. |
| **Main Screen** | File Manager — browse LittleFS files, upload files from your PC, read/edit files in-browser, and delete files over USB. |
| **Serial Cmd** | Interactive serial command terminal directly connected to Bruce's CLI (`help` for commands). |
| **Settings** | Configure WiFi credentials, reboot the board, view LittleFS/memory stats. |

---

## Key Features & Customizations

1. **BLE Media Commands**:
   - Replaced static shared Logitech MACs with the chip's factory hardware Bluetooth MAC, eliminating phantom auto-pairings.
   - Click stability fixed: clicking volume or media playback buttons stays within the controller rather than exiting to homescreen.
2. **Persistent Submenus**:
   - WiFi, Bluetooth, Files, RF, IR, RFID, and Others submenus remain open when you finish an attack, portal, or scan, returning to the submenu rather than dumping you to the main carousel.
3. **Automatic Real-Time Sync**:
   - Syncs internal software RTC automatically to your computer's exact clock on connection via `date set <epoch>`.
   - Clock app renders real time immediately with interactive timer and submenus.
4. **Maximized WiFi Output Power**:
   - Sets radio TX power to 19.5 dBm (`WIFI_POWER_19_5dBm`, 78 raw units) and disables modem sleep across all attacks and station modes.
5. **Onboard Status LED**:
   - Blue LED (GPIO 2) displays a gentle 2s heartbeat during normal operation and switches to a 10Hz rapid strobe during attacks.
   - *(Note: On DevKit V1, the Red LED is labeled `PWR` and hardwired to the 3.3V rail).*
6. **File Manager Over Cable**:
   - Chunked Base64 file writing (`writeb64`) enables uploading, editing, and deleting files via the WebUI without needing SD cards or WiFi.

---

## Building the Firmware From Source

If you want to modify the firmware or build it from scratch:

1. Open the [`source/`](file:///c:/Users/storm/OneDrive/Documents/work/source/) folder.
2. Run the builder:
   - **Windows**: `build.bat`
   - **Linux / macOS**: `./build.sh`
   - **Manual PlatformIO**: `python -m platformio run -e esp32-devkitv1`
3. The build script automatically packages the combined factory image to `bruce-devkitv1-port/Bruce-esp32-devkitv1.bin`.
4. Run `flash.bat` or `flash.sh` to write your new build to the board!

---

## Troubleshooting

- **Board not found / Unknown USB device**:
  - Ensure your micro-USB cable supports **data transfer** (many cheap phone cables only carry power).
  - Install the USB-to-UART driver for your board's chip:
    - **CP2102 / CP2104**: [Silicon Labs CP210x Driver](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
    - **CH340 / CH341**: [WCH Driver (Windows)](https://www.wch-ic.com/downloads/CH341SER_EXE.html) | [macOS Driver Guide](https://github.com/adrianmihalko/ch340g-ch34g-ch34x-mac-os-x-driver) | [SparkFun Driver Guide](https://learn.sparkfun.com/tutorials/how-to-install-ch340-drivers/all)
    - **FTDI**: [FTDI VCP Drivers](https://ftdichip.com/drivers/vcp-drivers/)
  - On Linux, check `dmesg | tail` or `ls /dev/ttyUSB* /dev/ttyACM*`.
  - On macOS, check `ls /dev/cu.usbserial*`.
- **Serial port busy**: Close any serial monitor (Arduino IDE, PuTTY, screen) before running `bruce` or `flash`.
- **Flashing bootloader timeout**: If the board doesn't auto-reset into download mode during flashing, hold down the **BOOT** button on the board, tap **RESET**, release **BOOT**, and run the flash script again.
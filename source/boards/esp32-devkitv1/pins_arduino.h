#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include <stdint.h>
#include "soc/soc_caps.h"

/*******************************************************************************************
 * ESP32 DevKit V1  (ESP32-D0WD-V3, WROOM-32, 4MB flash, NO PSRAM)
 *
 * Following the upstream convention, this header only declares pin constants.
 * All configuration macros live in esp32-devkitv1.ini
 *
 * Original-ESP32 constraints that MUST be respected:
 *   GPIO6..GPIO11  -> wired to the SPI flash, unusable
 *   GPIO34..GPIO39 -> INPUT ONLY (no output, no internal pull-up)
 *   GPIO0/2/12/15  -> strapping pins (GPIO12 must be LOW at boot)
 *   GPIO1/GPIO3    -> UART0 TX/RX, kept for flashing and the serial monitor
 *******************************************************************************************/

#define USB_VID 0x10C4
#define USB_PID 0xEA60

// UART0 - reserved for flashing / serial monitor
static const uint8_t TX = 1;
static const uint8_t RX = 3;

// Default I2C
static const uint8_t SDA = 21;
static const uint8_t SCL = 22;

// VSPI - the only hardware SPI bus on the original ESP32
static const uint8_t SS = 5;
static const uint8_t MOSI = 23;
static const uint8_t MISO = 19;
static const uint8_t SCK = 18;

// ADC channels
static const uint8_t A0 = 36;  // input only
static const uint8_t A1 = 39;  // input only
static const uint8_t A2 = 34;  // input only
static const uint8_t A3 = 35;  // input only
static const uint8_t A4 = 32;
static const uint8_t A5 = 33;
static const uint8_t A6 = 25;
static const uint8_t A7 = 26;

// Onboard blue LED
static const uint8_t LED_BUILTIN = 2;

// Safe general-purpose GPIOs
static const uint8_t G0 = 0;
static const uint8_t G2 = 2;
static const uint8_t G4 = 4;
static const uint8_t G5 = 5;
static const uint8_t G13 = 13;
static const uint8_t G14 = 14;
static const uint8_t G16 = 16;
static const uint8_t G17 = 17;
static const uint8_t G18 = 18;
static const uint8_t G19 = 19;
static const uint8_t G21 = 21;
static const uint8_t G22 = 22;
static const uint8_t G23 = 23;
static const uint8_t G25 = 25;
static const uint8_t G26 = 26;
static const uint8_t G27 = 27;
static const uint8_t G32 = 32;
static const uint8_t G33 = 33;

// Input-only pins (no output, no internal pull-up)
static const uint8_t G34 = 34;
static const uint8_t G35 = 35;
static const uint8_t G36 = 36;
static const uint8_t G39 = 39;

// Timers
static const uint8_t T1 = 1;
static const uint8_t T2 = 2;
static const uint8_t T3 = 3;
static const uint8_t T4 = 4;
static const uint8_t T5 = 5;
static const uint8_t T6 = 6;
static const uint8_t T7 = 7;
static const uint8_t T8 = 8;
static const uint8_t T9 = 9;
static const uint8_t T10 = 10;
static const uint8_t T11 = 11;
static const uint8_t T12 = 12;
static const uint8_t T13 = 13;
static const uint8_t T14 = 14;

#endif /* Pins_Arduino_h */

#pragma once
#include <Arduino.h>

#ifndef STATUS_LED_PIN
#define STATUS_LED_PIN 2
#endif

enum StatusLedMode {
    STATUS_LED_OFF = 0,
    STATUS_LED_NORMAL,  // gentle heartbeat blink every 2s
    STATUS_LED_ATTACK   // rapid alert strobe (10Hz)
};

void initStatusLed();
void setStatusLedMode(StatusLedMode mode);
void statusLedPulse(uint32_t durationMs = 40);

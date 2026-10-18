#include "status_led.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

static volatile StatusLedMode currentMode = STATUS_LED_NORMAL;
static volatile uint32_t pulseUntil = 0;

static void statusLedTask(void *pvParameters) {
    pinMode(STATUS_LED_PIN, OUTPUT);
    digitalWrite(STATUS_LED_PIN, LOW);

    uint32_t heartbeatCounter = 0;

    for (;;) {
        uint32_t now = millis();
        if (currentMode == STATUS_LED_ATTACK) {
            // Rapid alert strobe: 50ms ON, 50ms OFF (10Hz)
            digitalWrite(STATUS_LED_PIN, HIGH);
            vTaskDelay(pdMS_TO_TICKS(50));
            digitalWrite(STATUS_LED_PIN, LOW);
            vTaskDelay(pdMS_TO_TICKS(50));
            continue;
        }

        if (now < pulseUntil) {
            // Activity pulse
            digitalWrite(STATUS_LED_PIN, HIGH);
            vTaskDelay(pdMS_TO_TICKS(20));
            continue;
        }

        if (currentMode == STATUS_LED_NORMAL) {
            // Reassuring heartbeat: 30ms pulse every 2000ms
            if (++heartbeatCounter >= 40) { // 40 * 50ms = 2000ms
                heartbeatCounter = 0;
                digitalWrite(STATUS_LED_PIN, HIGH);
                vTaskDelay(pdMS_TO_TICKS(30));
                digitalWrite(STATUS_LED_PIN, LOW);
            } else {
                digitalWrite(STATUS_LED_PIN, LOW);
            }
        } else {
            digitalWrite(STATUS_LED_PIN, LOW);
        }

        vTaskDelay(pdMS_TO_TICKS(50));
    }
}

void initStatusLed() {
    static bool initialized = false;
    if (initialized) return;
    initialized = true;
    xTaskCreatePinnedToCore(statusLedTask, "statusLed", 2048, NULL, 1, NULL, 0);
}

void setStatusLedMode(StatusLedMode mode) {
    currentMode = mode;
}

void statusLedPulse(uint32_t durationMs) {
    pulseUntil = millis() + durationMs;
}

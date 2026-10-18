#include "powerSave.h"
#include "display.h"
#include "settings.h"

/* Check if it's time to put the device to sleep */
#define SCREEN_OFF_DELAY 5000

void fadeOutScreen(int startValue) {
    for (int brightValue = startValue; brightValue >= 0; brightValue -= 1) {
        setBrightness(max(brightValue, 0), false);
        delay(5);
    }
    turnOffDisplay();
}

void checkPowerSaveTime() {
#if defined(VIRTUAL_DISPLAY)
    // There is no backlight to dim and no panel to switch off. Screen-off also
    // suppresses every draw call (see tft_logger::isSleeping checks), which
    // would leave /getscreen permanently blank after the idle timeout. Keep the
    // virtual screen awake so the Navigator always has something to show.
    dimmer = false;
    isScreenOff = false;
    isSleeping = false;
    return;
#endif
    if (bruceConfig.dimmerSet == 0) return;

    unsigned long elapsed = millis() - previousMillis;
    int startDimmerBright = bruceConfig.bright / 3;
    int dimmerSetMs = bruceConfig.dimmerSet * 1000;

    if (elapsed >= dimmerSetMs && !dimmer && !isSleeping) {
        dimmer = true;
        setBrightness(startDimmerBright, false);
    } else if (elapsed >= (dimmerSetMs + SCREEN_OFF_DELAY) && !isScreenOff && !isSleeping) {
        isScreenOff = true;
        fadeOutScreen(startDimmerBright);
    }
}

void sleepModeOn() {
    isSleeping = true;
    setCpuFrequencyMhz(80);

    int startDimmerBright = bruceConfig.bright / 3;

    fadeOutScreen(startDimmerBright);

    panelSleep(true); //  power down screen

    disableCore0WDT();
#if SOC_CPU_CORES_NUM > 1
    disableCore1WDT();
#endif
    disableLoopWDT();
    delay(200);
}

void sleepModeOff() {
    isSleeping = false;
    setCpuFrequencyMhz(CONFIG_ESP_DEFAULT_CPU_FREQ_MHZ);

    panelSleep(false); // wake the screen back up

    getBrightness();
    enableCore0WDT();
#if SOC_CPU_CORES_NUM > 1
    enableCore1WDT();
#endif
    enableLoopWDT();
    feedLoopWDT();
    delay(200);
}

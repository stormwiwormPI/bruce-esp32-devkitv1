#include "ClockMenu.h"
#include "core/display.h"
#include "core/settings.h"
#include "modules/others/timer.h"

void ClockMenu::optionsMenu() {
    returnToMenu = false;
    while (!returnToMenu) {
        runClockLoop(true);

        // If ESC is pressed, it exits
        if (returnToMenu) break;

        // OK pressed, show submenu
        showSubMenu();

        // If "Exit" or ESC is pressed in submenu, it exits
        if (returnToMenu) break;
    }
    returnToMenu = false;
}

void ClockMenu::showSubMenu() {
    options = {
        {"Timer",         [=]() { Timer(); } },
        {"Back to Clock", [=]() { returnToMenu = false; } },
        {"Exit",          [=]() { returnToMenu = true; }}
    };

    delay(100);
    int res = loopOptions(options);
    if (res < 0 || res == 2) {
        returnToMenu = true;
    } else if (res == 1) {
        returnToMenu = false;
    }
}

void ClockMenu::drawIcon(float scale) {
    clearIconArea();
    int radius = scale * 30;
    int pointerSize = scale * 15;

    // Case
    tft.drawArc(
        iconCenterX, iconCenterY, 1.1 * radius, radius, 0, 360, bruceConfig.priColor, bruceConfig.bgColor
    );

    // Pivot center
    tft.fillCircle(iconCenterX, iconCenterY, radius / 10, bruceConfig.priColor);

    // Hours & minutes
    tft.drawLine(
        iconCenterX,
        iconCenterY,
        iconCenterX - 2 * pointerSize / 3,
        iconCenterY - 2 * pointerSize / 3,
        bruceConfig.priColor
    );
    tft.drawLine(
        iconCenterX, iconCenterY, iconCenterX + pointerSize, iconCenterY - pointerSize, bruceConfig.priColor
    );
}

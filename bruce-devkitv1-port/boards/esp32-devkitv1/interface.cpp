#include "core/powerSave.h"
#include <interface.h>

/***************************************************************************************
** Function name: _setup_gpio()
** Location: main.cpp
** Description:   initial setup for the device
**
** This board has NO display, so we boot straight into the WebUI, which is
** served over the device's own WiFi access point. The PC browser becomes
** the screen.
***************************************************************************************/
void _setup_gpio() { bruceConfig.startupApp = "WebUI"; }

/***************************************************************************************
** Function name: getBattery()
** location: display.cpp
** Description:   Delivers the battery value from 0-100
***************************************************************************************/
int getBattery() { return 0; }

/*********************************************************************
** Function: isCharging
** location: display.cpp
** Description:   Default implementation that returns false
**********************************************************************/
bool isCharging() { return false; }

/*********************************************************************
** Function: setBrightness
** location: settings.cpp
** set brightness value
**********************************************************************/
void _setBrightness(uint8_t brightval) {}

/*********************************************************************
** Function: InputHandler
** Handles the variables PrevPress, NextPress, SelPress, AnyKeyPress and EscPress
**
** No buttons on a bare DevKit V1 - input comes from the WebUI or serial.
**********************************************************************/
void InputHandler(void) {}

/*********************************************************************
** Function: powerOff
** location: mykeyboard.cpp
** Turns off the device (or try to)
**********************************************************************/
void powerOff() {}

/*********************************************************************
** Function: checkReboot
** location: mykeyboard.cpp
** Btn logic to turnoff the device (name is odd btw)
**********************************************************************/
void checkReboot() {}

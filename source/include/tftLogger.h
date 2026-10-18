#ifndef __DISPLAY_LOGER
#define __DISPLAY_LOGER
#if defined(HAS_SCREEN) && !defined(VIRTUAL_DISPLAY)
#include <display/tft.h>
#define BRUCE_TFT_DRIVER tft_display
#else
// VIRTUAL_DISPLAY: HAS_SCREEN is set so the graphical menu compiles and runs,
// but no panel is fitted. Keep the pure-software renderer so no SPI traffic
// is generated; getBinLog() still returns the real menu as draw commands.
#include <VectorDisplay.h>
#define BRUCE_TFT_DRIVER SerialDisplayClass
#endif
enum tftFuncs : uint8_t { // DO NOT CHANGE THE ORDER, ADD NEW FUNCTIONS TO THE END!!!
    FILLSCREEN,           // 0
    DRAWRECT,             // 1
    FILLRECT,             // 2
    DRAWROUNDRECT,        // 3
    FILLROUNDRECT,        // 4
    DRAWCIRCLE,           // 5
    FILLCIRCLE,           // 6
    DRAWTRIAGLE,          // 7
    FILLTRIANGLE,         // 8
    DRAWELIPSE,           // 9
    FILLELIPSE,           // 10
    DRAWLINE,             // 11
    DRAWARC,              // 12
    DRAWWIDELINE,         // 13
    DRAWCENTRESTRING,     // 14
    DRAWRIGHTSTRING,      // 15
    DRAWSTRING,           // 16
    PRINT,                // 17
    DRAWIMAGE,            // 18
    DRAWPIXEL,            // 19
    DRAWFASTVLINE,        // 20
    DRAWFASTHLINE,        // 21
    // Add new ones here

    SCREEN_INFO = 99 // 99
};
#if defined(BOARD_HAS_PSRAM)
#define MAX_LOG_ENTRIES 64
#define MAX_LOG_SIZE 128
#define MAX_LOG_IMAGES 1
#define MAX_LOG_IMG_PATH 512
#else
#define MAX_LOG_ENTRIES 96
#define MAX_LOG_SIZE 64
#define MAX_LOG_IMAGES 1
#define MAX_LOG_IMG_PATH 256
#endif
#define LOG_PACKET_HEADER 0xAA

struct tftLog {
    uint8_t data[MAX_LOG_SIZE];
};
class tft_logger : public BRUCE_TFT_DRIVER {
private:
    tftLog *log = nullptr;
    // VIRTUAL_DISPLAY: VectorDisplay's setTextDatum() is a no-op mockup with no
    // getter, but display.cpp saves and restores the datum under HAS_SCREEN.
    uint8_t textdatum = TC_DATUM;
    char (*images)[MAX_LOG_IMG_PATH] = nullptr;
    uint8_t logWriteIndex = 0;
    uint8_t logCount = 0;
    bool isSleeping = false;
    bool logging = false;
    bool _logging = false;
    void clearLog();
    bool async_serial = false;
    TaskHandle_t asyncSerialTask = NULL;
    QueueHandle_t asyncSerialQueue = NULL;
    static void asyncSerialTaskFunc(void *pv);
    inline uint8_t currentTextSize() const {
#if defined(HAS_SCREEN) && !defined(VIRTUAL_DISPLAY)
        return getTextSize();
#else
        return textsize;
#endif
    }
    inline uint16_t currentTextColor() const {
#if defined(HAS_SCREEN) && !defined(VIRTUAL_DISPLAY)
        return getTextColor();
#else
        return textcolor;
#endif
    }
    inline uint16_t currentTextBgColor() const {
#if defined(HAS_SCREEN) && !defined(VIRTUAL_DISPLAY)
        return getTextBgColor();
#else
        return textbgcolor;
#endif
    }

public:
    tft_logger(int16_t w = TFT_WIDTH, int16_t h = TFT_HEIGHT);
    virtual ~tft_logger();

    // VIRTUAL_DISPLAY: see the note on the member above.
    void setTextDatum(uint8_t d) { textdatum = d; }
    uint8_t getTextDatum() { return textdatum; }

    // VIRTUAL_DISPLAY: main.cpp calls tft.init() under HAS_SCREEN. The hardware
    // backend has init(); VectorDisplay spells it begin().
    void init() { begin(); }

    // VIRTUAL_DISPLAY: sprite/draw alias this logger, so the few places that
    // drive an off-screen sprite need these to exist. They are no-ops here -
    // drawing goes straight to the log.
    void createSprite(int16_t w, int16_t h) {}
    void deleteSprite() {}
    void pushSprite(int16_t x, int16_t y, bool transparent = false) {}

    // VIRTUAL_DISPLAY: gradient fills are TFT_eSPI-only. Definitions follow
    // the class, once tft_logger is complete.
    void fillRectHGradient(int16_t x, int16_t y, int16_t w, int16_t h,
                           uint16_t c1, uint16_t c2);
    void fillRectVGradient(int16_t x, int16_t y, int16_t w, int16_t h,
                           uint16_t c1, uint16_t c2);
    void setLogging(bool _log = true);
    bool inline getLogging(void) { return logging; };

    // Disables tft writings on the display,
    // Commands wont be passed to the display if isSleeping==true
    // display will still be logged, in order to keep WebUI Navigator working
    void inline setSleepMode(bool mode) { isSleeping = mode; }

    void getBinLog(uint8_t *outBuffer, size_t &outSize);
    bool removeLogEntriesInsideRect(int rx, int ry, int rw, int rh);
    void removeOverlappedImages(int x, int y, int center, int ms);

    void fillScreen(int32_t color);
    void startAsyncSerial();
    void stopAsyncSerial();
    void getTftInfo();
    void imageToBin(uint8_t fs, String file, int x, int y, bool center, int Ms);

    void drawLine(int32_t x, int32_t y, int32_t x1, int32_t y1, int32_t color);
    void drawRect(int32_t x, int32_t y, int32_t w, int32_t h, int32_t color);
    void fillRect(int32_t x, int32_t y, int32_t w, int32_t h, int32_t color);
    void drawRoundRect(int32_t x, int32_t y, int32_t w, int32_t h, int32_t r, int32_t color);
    void fillRoundRect(int32_t x, int32_t y, int32_t w, int32_t h, int32_t r, int32_t color);

    void drawCircle(int32_t x, int32_t y, int32_t r, int32_t color);
    void fillCircle(int32_t x, int32_t y, int32_t r, int32_t color);
    void drawEllipse(int16_t x, int16_t y, int32_t rx, int32_t ry, uint16_t color);
    void fillEllipse(int16_t x, int16_t y, int32_t rx, int32_t ry, uint16_t color);
    void drawTriangle(int32_t x1, int32_t y1, int32_t x2, int32_t y2, int32_t x3, int32_t y3, int32_t color);
    void fillTriangle(int32_t x1, int32_t y1, int32_t x2, int32_t y2, int32_t x3, int32_t y3, int32_t color);
    void drawArc(
        int32_t x, int32_t y, int32_t r, int32_t ir, uint32_t startAngle, uint32_t endAngle,
        uint32_t fg_color, uint32_t bg_color, bool smoothArc = 1
    );
    void drawWideLine(float ax, float ay, float bx, float by, float wd, int32_t fg, int32_t bg = 0x00FFFFFF);
    void drawFastVLine(int32_t x, int32_t y, int32_t h, int32_t fg);
    void drawFastHLine(int32_t x, int32_t y, int32_t w, int32_t fg);
    void log_drawString(String s, tftFuncs fn, int32_t x, int32_t y);
    int16_t drawString(const String &string, int32_t x, int32_t y, uint8_t font = 1);
    int16_t drawCentreString(const String &string, int32_t x, int32_t y, uint8_t font = 1);
    int16_t drawRightString(const String &string, int32_t x, int32_t y, uint8_t font = 1);

    void log_print(String s);

    size_t print(const String &s);
    size_t println(const String &s);
    size_t println(void);

    size_t println(char c);
    size_t println(unsigned char b, int base);
    size_t println(int n, int base);
    size_t println(unsigned int n, int base);
    size_t println(long n, int base);
    size_t println(unsigned long n, int base);
    size_t println(long long n, int base);
    size_t println(unsigned long long n, int base);
    size_t println(double n, int digits);

    size_t print(char c);
    size_t print(unsigned char b, int base);
    size_t print(int n, int base);
    size_t print(unsigned int n, int base);
    size_t print(long n, int base);
    size_t print(unsigned long n, int base);
    size_t print(long long n, int base);
    size_t print(unsigned long long n, int base);
    size_t print(double n, int digits);
    size_t printf(const char *format, ...);

protected:
    bool isLogEqual(const tftLog &a, const tftLog &b);
    void pushLogIfUnique(const tftLog &l);
    // void checkAndLog(tftFuncs f, std::initializer_list<int32_t> values);
    template <typename... Args> void checkAndLog(tftFuncs f, Args... args) {
        if (!logging) return;

        uint8_t buffer[MAX_LOG_SIZE];
        uint8_t pos = 0;
        logWriteHeader(buffer, pos, f);

        (writeUint16(buffer, pos, static_cast<uint16_t>(args)), ...);
        buffer[1] = pos;

        tftLog l;
        memcpy(l.data, buffer, pos);
        pushLogIfUnique(l);
        if (isSleeping) return;
        logging = false;
    }
    void restoreLogger();
    void addLogEntry(const uint8_t *buffer, uint8_t size);
    void logWriteHeader(uint8_t *buffer, uint8_t &pos, tftFuncs fn);
    void writeUint16(uint8_t *buffer, uint8_t &pos, uint16_t value);
};

#if defined(VIRTUAL_DISPLAY)
// The JS interpreter's display module names the hardware types directly
// (tft_display, tft_sprite). With the software renderer both are the logger,
// so alias them here rather than patching every call site.
typedef tft_logger tft_display;
typedef tft_logger tft_sprite;

// Gradient fills exist only on TFT_eSPI. Approximate with the average colour,
// which keeps JS display calls working on the software renderer.
inline void tft_logger::fillRectHGradient(int16_t x, int16_t y, int16_t w, int16_t h,
                                           uint16_t c1, uint16_t c2) {
    fillRect(x, y, w, h, (uint16_t)((((c1 >> 1) & 0x7BE0) + ((c2 >> 1) & 0x7BE0)) >> 1));
}
inline void tft_logger::fillRectVGradient(int16_t x, int16_t y, int16_t w, int16_t h,
                                           uint16_t c1, uint16_t c2) {
    fillRect(x, y, w, h, (uint16_t)((((c1 >> 1) & 0x7BE0) + ((c2 >> 1) & 0x7BE0)) >> 1));
}
#endif

#endif //__DISPLAY_LOGER

// Under VIRTUAL_DISPLAY display/tft.h must stay out: it declares TFT_eSPI's own
// tft_display and colour macros, which collide with the tft_logger alias and
// tftLogger.h's definitions. Take the alias from tftLogger.h instead and define
// the two colours locally.
#if defined(VIRTUAL_DISPLAY)
#include <tftLogger.h>
#define TFT_BLACK 0x0000
#define TFT_WHITE 0xFFFF
#else
#include <display/tft.h>
#endif

class QRcode
{
	private:
		tft_display *tft;
		void render(int x, int y, int color);

	public:
		QRcode(tft_display *display);
		void init();
		void create(String message);	
};

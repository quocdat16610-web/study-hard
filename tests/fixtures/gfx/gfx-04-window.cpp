#include "font.h"
#include "gfx.h"

static volatile u32 *fb;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > W ? W : x + w, y1 = y + h > H ? H : y + h;
    for (int py = y0; py < y1; py++) {
        for (int px = x0; px < x1; px++) fb[py * W + px] = color;
    }
}

static void draw_text(int x, int y, const char *s, u32 color) {
    for (; *s; s++, x += FONT_ADVANCE) {
        const unsigned char *glyph = FONT[static_cast<u8>(*s) & 127];
        for (int row = 0; row < FONT_H; row++) {
            for (int col = 0; col < FONT_W; col++) {
                if (glyph[row] & (0x10 >> col)) fill_rect(x + col, y + row, 1, 1, color);
            }
        }
    }
}

static void draw_window(int x, int y, int w, int h, const char *title, bool active) {
    fill_rect(x, y, w, h, 0x000000);
    fill_rect(x + 1, y + 1, w - 2, h - 2, 0xC0C0C0);
    fill_rect(x + 1, y + 1, w - 2, 12, active ? 0x000080 : 0x808080);
    draw_text(x + 4, y + 3, title, 0xFFFFFF);
    fill_rect(x + w - 11, y + 3, 8, 8, 0xFF0000);
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    draw_window(30, 20, 180, 100, "FILES", true);
    draw_text(36, 40, "3 ITEMS", 0x000000);
    draw_window(120, 130, 150, 60, "NOTES", false);
    serial_print("GFX OK\n");
    halt();
}

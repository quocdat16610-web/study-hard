#include "font.h"
#include "gfx.h"

static volatile u32 *fb;

static void put_pixel(int x, int y, u32 color) {
    if (x >= 0 && x < W && y >= 0 && y < H) fb[y * W + x] = color;
}

static void draw_char(int x, int y, char ch, u32 color) {
    const unsigned char *glyph = FONT[static_cast<u8>(ch) & 127];
    for (int row = 0; row < FONT_H; row++) {
        for (int col = 0; col < FONT_W; col++) {
            if (glyph[row] & (0x10 >> col)) put_pixel(x + col, y + row, color);
        }
    }
}

static void draw_text(int x, int y, const char *s, u32 color) {
    int cx = x;
    for (; *s; s++) {
        if (*s == '\n') {
            cx = x;
            y += FONT_H + 2;
            continue;
        }
        draw_char(cx, y, *s, color);
        cx += FONT_ADVANCE;
    }
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    for (int i = 0; i < W * H; i++) fb[i] = 0x000080;
    draw_text(8, 8, "HELLO OS", 0xFFFFFF);
    draw_text(8, 24, "320X200\nPIXELS", 0xFFFF00);
    serial_print("GFX OK\n");
    halt();
}

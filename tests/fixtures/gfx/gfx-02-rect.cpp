#include "gfx.h"

static volatile u32 *fb;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > W ? W : x + w, y1 = y + h > H ? H : y + h;
    for (int py = y0; py < y1; py++) {
        for (int px = x0; px < x1; px++) fb[py * W + px] = color;
    }
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    fill_rect(0, 184, W, 16, 0xC0C0C0);
    fill_rect(40, 30, 200, 120, 0xFFFFFF);
    fill_rect(40, 30, 200, 14, 0x000080);
    fill_rect(300, -10, 50, 30, 0xFFFF00);
    fill_rect(-20, 170, 40, 60, 0xFF00FF);
    serial_print("GFX OK\n");
    halt();
}

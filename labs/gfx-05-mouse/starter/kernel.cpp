#include "gfx.h"

static volatile u32 *fb;
static const int CURSOR = 5;
static int cx = 160, cy = 100;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    for (int py = y; py < y + h; py++) {
        for (int px = x; px < x + w; px++) fb[py * W + px] = color;
    }
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    fill_rect(100, 60, 60, 40, 0xFF0000);
    mouse_init();
    fill_rect(cx, cy, CURSOR, CURSOR, 0xFFFFFF);
    serial_print("GFX OK\n");
    for (;;) {
        u8 byte;
        if (!mouse_poll(byte)) continue;
        // TODO: gom 3 byte thành một gói (đồng bộ bằng bit 3 của byte đầu), tính dx và dy có dấu,
        //       ẩn con trỏ (khôi phục nền), cập nhật cx/cy có chặn biên, hiện con trỏ (lưu nền mới)
    }
}

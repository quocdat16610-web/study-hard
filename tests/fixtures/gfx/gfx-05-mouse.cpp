#include "gfx.h"

static volatile u32 *fb;
static const int CURSOR = 5;
static u32 saved[CURSOR * CURSOR];
static int cx = 160, cy = 100;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    for (int py = y; py < y + h; py++) {
        for (int px = x; px < x + w; px++) fb[py * W + px] = color;
    }
}

static void cursor_show() {
    for (int y = 0; y < CURSOR; y++) {
        for (int x = 0; x < CURSOR; x++) {
            saved[y * CURSOR + x] = fb[(cy + y) * W + cx + x];
            fb[(cy + y) * W + cx + x] = 0xFFFFFF;
        }
    }
}

static void cursor_hide() {
    for (int y = 0; y < CURSOR; y++) {
        for (int x = 0; x < CURSOR; x++) fb[(cy + y) * W + cx + x] = saved[y * CURSOR + x];
    }
}

static int clamp(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    fill_rect(100, 60, 60, 40, 0xFF0000);
    mouse_init();
    cursor_show();
    serial_print("GFX OK\n");
    u8 packet[3];
    int n = 0;
    for (;;) {
        u8 byte;
        if (!mouse_poll(byte)) continue;
        if (n == 0 && !(byte & 0x08)) continue;  // resynchronise: the first byte always has bit 3 set
        packet[n++] = byte;
        if (n < 3) continue;
        n = 0;
        const int dx = packet[1] - ((packet[0] & 0x10) ? 256 : 0);
        const int dy = packet[2] - ((packet[0] & 0x20) ? 256 : 0);
        cursor_hide();
        cx = clamp(cx + dx, 0, W - CURSOR);
        cy = clamp(cy - dy, 0, H - CURSOR);
        cursor_show();
    }
}

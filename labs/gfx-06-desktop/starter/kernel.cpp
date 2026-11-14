#include "font.h"
#include "gfx.h"

struct Window {
    int x, y, w, h;
    const char *title;
};

static volatile u32 *fb;
static Window wins[2] = {{20, 20, 140, 90, "A"}, {100, 60, 140, 90, "B"}};
static int cx = 160, cy = 100;

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

static void draw_window(const Window &win, bool active) {
    fill_rect(win.x, win.y, win.w, win.h, 0x000000);
    fill_rect(win.x + 1, win.y + 1, win.w - 2, win.h - 2, 0xC0C0C0);
    fill_rect(win.x + 1, win.y + 1, win.w - 2, 12, active ? 0x000080 : 0x808080);
    draw_text(win.x + 4, win.y + 3, win.title, 0xFFFFFF);
    fill_rect(win.x + win.w - 11, win.y + 3, 8, 8, 0xFF0000);
}

// Gom một gói tin chuột. Trả về true khi đủ 3 byte; dx, dy theo trục màn hình (dy dương = đi xuống).
static bool mouse_read(int &dx, int &dy, bool &left) {
    static u8 packet[3];
    static int n = 0;
    u8 byte;
    if (!mouse_poll(byte)) return false;
    if (n == 0 && !(byte & 0x08)) return false;
    packet[n++] = byte;
    if (n < 3) return false;
    n = 0;
    dx = packet[1] - ((packet[0] & 0x10) ? 256 : 0);
    dy = -(packet[2] - ((packet[0] & 0x20) ? 256 : 0));
    left = packet[0] & 1;
    return true;
}

static int clamp(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    mouse_init();
    fill_rect(0, 0, W, H, 0x008080);
    draw_window(wins[0], true);
    draw_window(wins[1], false);  // B đang đè lên A dù A mới là cửa sổ active
    serial_print("GFX OK\n");
    for (;;) {
        int dx, dy;
        bool left;
        if (!mouse_read(dx, dy, left)) continue;
        cx = clamp(cx + dx, 0, W - 5);
        cy = clamp(cy + dy, 0, H - 5);
        // TODO: back buffer + compose(); z-order theo `top`; click trái (cạnh lên) đưa cửa sổ dưới con trỏ lên trên
        fill_rect(cx, cy, 5, 5, left ? 0xFFFF00 : 0xFFFFFF);  // vẽ thẳng lên màn hình: con trỏ để lại vệt
    }
}

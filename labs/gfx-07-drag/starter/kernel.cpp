#include "font.h"
#include "gfx.h"

struct Window {
    int x, y, w, h;
    const char *title;
};

static volatile u32 *fb;
static u32 back[W * H];
static Window wins[2] = {{20, 20, 140, 90, "A"}, {100, 60, 140, 90, "B"}};
static int top = 0;
static int cx = 160, cy = 100;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > W ? W : x + w, y1 = y + h > H ? H : y + h;
    for (int py = y0; py < y1; py++) {
        for (int px = x0; px < x1; px++) back[py * W + px] = color;
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

static void compose() {
    fill_rect(0, 0, W, H, 0x008080);
    draw_window(wins[1 - top], false);
    draw_window(wins[top], true);
    fill_rect(cx, cy, 5, 5, 0xFFFFFF);
    for (int i = 0; i < W * H; i++) fb[i] = back[i];  // one copy: the screen never shows a half-drawn frame
}

static bool inside(const Window &win, int x, int y) {
    return x >= win.x && x < win.x + win.w && y >= win.y && y < win.y + win.h;
}

static int clamp(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    mouse_init();
    compose();
    serial_print("GFX OK\n");
    u8 packet[3];
    int n = 0;
    bool was_down = false;
    for (;;) {
        u8 byte;
        if (!mouse_poll(byte)) continue;
        if (n == 0 && !(byte & 0x08)) continue;
        packet[n++] = byte;
        if (n < 3) continue;
        n = 0;
        cx = clamp(cx + packet[1] - ((packet[0] & 0x10) ? 256 : 0), 0, W - 5);
        cy = clamp(cy - (packet[2] - ((packet[0] & 0x20) ? 256 : 0)), 0, H - 5);
        const bool down = packet[0] & 1;
        if (down && !was_down && !inside(wins[top], cx, cy) && inside(wins[1 - top], cx, cy)) top = 1 - top;
        // TODO: nhấn trên thanh tiêu đề (cy < win.y + 13) bắt đầu kéo và ghi lại điểm nắm;
        //       nhả nút thì dừng; khi đang kéo, cửa sổ đi theo con trỏ (win.x = cx - grab_x, ...)
        was_down = down;
        compose();
    }
}

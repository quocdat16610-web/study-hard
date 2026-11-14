#include "ui.h"

struct Window {
    int r, c, h, w;
    const char *title;
    char text[24];
    int n;
};

static Window wins[2] = {{2, 5, 10, 30, " A ", {}, 0}, {6, 20, 10, 30, " B ", {}, 0}};
static const u8 BODY = attr(BLACK, LIGHT_GREY), ACTIVE = attr(WHITE, BLUE), DESK = attr(LIGHT_GREY, CYAN);

static void put(int r, int c, char ch, u8 a) { VGA[r * COLS + c] = cell(ch, a); }

static void draw(const Window &win, bool focused) {
    for (int y = 0; y < win.h; y++) {
        for (int x = 0; x < win.w; x++) {
            const bool top = y == 0, bottom = y == win.h - 1, left = x == 0, right = x == win.w - 1;
            char ch = ' ';
            if (top && left) ch = BOX_TL;
            else if (top && right) ch = BOX_TR;
            else if (bottom && left) ch = BOX_BL;
            else if (bottom && right) ch = BOX_BR;
            else if (top || bottom) ch = BOX_H;
            else if (left || right) ch = BOX_V;
            put(win.r + y, win.c + x, ch, top && focused ? ACTIVE : BODY);
        }
    }
    for (int i = 0; win.title[i]; i++) put(win.r, win.c + 2 + i, win.title[i], focused ? ACTIVE : BODY);
    for (int i = 0; i < win.n; i++) put(win.r + 1, win.c + 1 + i, win.text[i], BODY);
}

static void repaint(int focus) {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', DESK);
    draw(wins[1 - focus], false);  // painter's algorithm: back to front
    draw(wins[focus], true);
}

extern "C" void kmain() {
    int focus = 0;
    repaint(focus);
    for (;;) {
        const u8 sc = kbd_scancode();
        if (sc & 0x80) continue;
        Window &win = wins[focus];
        if (sc == KEY_TAB) focus = 1 - focus;
        else if (const char ch = KEYMAP[sc]; ch >= ' ' && win.n < 23) win.text[win.n++] = ch;
        else continue;
        repaint(focus);
    }
}

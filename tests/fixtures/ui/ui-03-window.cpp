#include "ui.h"

static void put(int r, int c, char ch, u8 a) { VGA[r * COLS + c] = cell(ch, a); }

static int length(const char *s) {
    int n = 0;
    while (s[n]) n++;
    return n;
}

static void window(int r, int c, int h, int w, const char *title, u8 a) {
    for (int y = 0; y < h; y++) {
        for (int x = 0; x < w; x++) {
            const bool top = y == 0, bottom = y == h - 1, left = x == 0, right = x == w - 1;
            char ch = ' ';
            if (top && left) ch = BOX_TL;
            else if (top && right) ch = BOX_TR;
            else if (bottom && left) ch = BOX_BL;
            else if (bottom && right) ch = BOX_BR;
            else if (top || bottom) ch = BOX_H;
            else if (left || right) ch = BOX_V;
            put(r + y, c + x, ch, a);
        }
    }
    const int n = length(title), start = c + (w - n) / 2;
    for (int i = 0; i < n; i++) put(r, start + i, title[i], a);
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', attr(WHITE, BLUE));
    window(5, 20, 10, 40, " Hello ", attr(BLACK, LIGHT_GREY));
    serial_print("UI OK\n");
    halt();
}

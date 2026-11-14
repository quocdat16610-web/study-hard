#include "ui.h"

static const u8 NORMAL = attr(LIGHT_GREY, BLACK), INVERSE = attr(BLACK, LIGHT_GREY);
static const char *const ITEMS[3] = {"Open", "Save", "Quit"};

static void text(int r, int c, const char *s, u8 a) {
    for (; *s; s++, c++) VGA[r * COLS + c] = cell(*s, a);
}

static void bar(int r, const char *s) {
    for (int x = 0; x < COLS; x++) VGA[r * COLS + x] = cell(' ', INVERSE);
    text(r, 1, s, INVERSE);
}

static void draw(int selected) {
    for (int i = 0; i < 3; i++) {
        const u8 a = i == selected ? INVERSE : NORMAL;
        for (int x = 2; x < 22; x++) VGA[(2 + i) * COLS + x] = cell(' ', a);
        text(2 + i, 4, ITEMS[i], a);
    }
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', NORMAL);
    bar(0, "MENU");
    bar(24, "Up/Down: move   Enter: select");
    int selected = 0;
    draw(selected);
    for (;;) {
        const u8 sc = kbd_scancode();
        // TODO: nhớ tiền tố 0xE0; KEY_UP / KEY_DOWN đổi selected (đi vòng); KEY_ENTER ghi "Selected: ..." lên hàng 24
        if (sc == KEY_ENTER) bar(24, "Selected: ?");
        draw(selected);
    }
}

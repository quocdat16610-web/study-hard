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
    bool extended = false;
    draw(selected);
    for (;;) {
        const u8 sc = kbd_scancode();
        if (sc == 0xE0) {
            extended = true;
            continue;
        }
        const bool ext = extended;
        extended = false;
        if (sc & 0x80) continue;
        if (ext && sc == KEY_UP) selected = (selected + 2) % 3;
        else if (ext && sc == KEY_DOWN) selected = (selected + 1) % 3;
        else if (!ext && sc == KEY_ENTER) {
            bar(24, "Selected: ");
            text(24, 11, ITEMS[selected], INVERSE);
        }
        draw(selected);
    }
}

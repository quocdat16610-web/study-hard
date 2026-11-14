#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void clear() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    row = col = 0;
}

static void putc(char ch) {
    if (ch == '\n') {
        col = 0;
        row++;
        return;
    }
    VGA[row * COLS + col] = cell(ch, A);
    if (++col == COLS) {
        col = 0;
        row++;
    }
}

static void print(const char *s) { while (*s) putc(*s++); }

extern "C" void kmain() {
    clear();
    print("Line 1\nLine 2\n");
    for (int i = 0; i < 100; i++) putc('x');
    serial_print("UI OK\n");
    halt();
}

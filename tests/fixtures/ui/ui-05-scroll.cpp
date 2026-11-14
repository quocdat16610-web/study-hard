#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void scroll() {
    for (int i = 0; i < (ROWS - 1) * COLS; i++) VGA[i] = VGA[i + COLS];
    for (int i = (ROWS - 1) * COLS; i < ROWS * COLS; i++) VGA[i] = cell(' ', A);
    row = ROWS - 1;
}

static void putc(char ch) {
    if (ch == '\n') {
        col = 0;
        row++;
    } else {
        VGA[row * COLS + col] = cell(ch, A);
        if (++col == COLS) {
            col = 0;
            row++;
        }
    }
    if (row == ROWS) scroll();
}

static void print(const char *s) { while (*s) putc(*s++); }

static void print_num(int v) {
    char digits[12];
    int n = 0;
    do {
        digits[n++] = static_cast<char>('0' + v % 10);
        v /= 10;
    } while (v > 0);
    while (n > 0) putc(digits[--n]);
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    for (int i = 0; i < 30; i++) {
        print("line ");
        print_num(i);
        putc('\n');
    }
    serial_print("UI OK\n");
    halt();
}

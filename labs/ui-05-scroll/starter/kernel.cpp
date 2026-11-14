#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

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
    // TODO: nếu row vượt quá hàng cuối thì cuộn màn hình lên một hàng
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

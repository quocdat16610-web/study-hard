#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void clear() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    row = col = 0;
}

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

static void read_line(char *line, int cap) {
    int n = 0;
    for (;;) {
        const u8 sc = kbd_scancode();
        if (sc & 0x80) continue;
        if (sc == KEY_ENTER) break;
        if (sc == KEY_BACKSPACE) {
            if (n > 0 && col > 0) {
                n--;
                col--;
                VGA[row * COLS + col] = cell(' ', A);
            }
        } else if (const char ch = KEYMAP[sc]; ch >= ' ' && n < cap - 1) {
            line[n++] = ch;
            putc(ch);
        }
    }
    line[n] = 0;
    putc('\n');
}

static void run(const char *line) {
    // TODO: dòng rỗng; "help"; "echo <văn bản>"; "clear"; lệnh lạ
    print("unknown command: ");
    print(line);
    putc('\n');
}

extern "C" void kmain() {
    clear();
    char line[64];
    for (;;) {
        print("os> ");
        read_line(line, 64);
        run(line);
    }
}

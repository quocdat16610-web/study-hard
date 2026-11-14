#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void putc(char ch) {
    if (ch == '\n') {
        col = 0;
        row++;
        return;
    }
    VGA[row * COLS + col] = cell(ch, A);
    col++;
}

static void print(const char *s) { while (*s) putc(*s++); }

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    print("> ");
    char line[64];
    int n = 0;
    for (;;) {
        const u8 sc = kbd_scancode();
        if (sc & 0x80) continue;
        if (sc == KEY_ENTER) {
            line[n] = 0;
            putc('\n');
            print("You typed: ");
            print(line);
            print("\n> ");
            n = 0;
        } else if (sc == KEY_BACKSPACE) {
            if (n > 0) {
                n--;
                col--;
                VGA[row * COLS + col] = cell(' ', A);
            }
        } else if (const char ch = KEYMAP[sc]; ch >= ' ' && n < 63) {
            line[n++] = ch;
            putc(ch);
        }
    }
}

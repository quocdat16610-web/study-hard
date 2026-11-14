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
    for (;;) {
        const u8 sc = kbd_scancode();
        // TODO: bỏ qua break code (nhả phím); lưu ký tự vào bộ đệm; xử lý KEY_BACKSPACE và KEY_ENTER
        putc(KEYMAP[sc & 0x7F]);
    }
}

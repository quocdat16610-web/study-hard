#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void putc(char ch) {
    // TODO: xử lý '\n' (về đầu dòng kế tiếp) và tự xuống dòng khi col chạm COLS
    VGA[row * COLS + col] = cell(ch, A);
    col++;
}

static void print(const char *s) { while (*s) putc(*s++); }

extern "C" void kmain() {
    // TODO: xoá màn hình trước khi in (màn hình đang còn chữ của BIOS)
    print("Line 1\nLine 2\n");
    for (int i = 0; i < 100; i++) putc('x');
    serial_print("UI OK\n");
    halt();
}

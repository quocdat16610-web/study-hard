#include "ui.h"

static void put(int r, int c, char ch, u8 a) { VGA[r * COLS + c] = cell(ch, a); }

static void window(int r, int c, int h, int w, const char *title, u8 a) {
    put(r, c, BOX_TL, a);
    // TODO: 3 góc còn lại, viền ngang/dọc, phần ruột (dấu cách), tiêu đề căn giữa trên viền trên
    put(r + h - 1, c + w - 1, title[0], a);  // dòng tạm để dùng hết tham số; hãy thay bằng mã của bạn
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', attr(WHITE, BLUE));
    window(5, 20, 10, 40, " Hello ", attr(BLACK, LIGHT_GREY));
    serial_print("UI OK\n");
    halt();
}

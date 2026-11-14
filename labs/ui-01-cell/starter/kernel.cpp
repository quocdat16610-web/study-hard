#include "ui.h"

extern "C" void kmain() {
    // Một ô mẫu: dấu '?' trắng trên nền đỏ ở góc trên trái. Thử đổi ký tự, màu, vị trí rồi bấm "Chạy thử".
    VGA[0] = cell('?', attr(WHITE, RED));

    // TODO 1: tô toàn màn hình bằng dấu cách, thuộc tính attr(WHITE, BLUE)
    // TODO 2: in "OS" màu YELLOW trên nền BLUE tại hàng 12, cột 39
    // TODO 3: serial_print("UI OK\n");
    halt();
}

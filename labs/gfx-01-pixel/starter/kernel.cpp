#include "gfx.h"

extern "C" void kmain() {
    volatile u32 *fb = fb_init();
    if (!fb) halt();

    // Ba điểm mẫu ở góc trên trái. Thử đổi toạ độ và màu rồi bấm "Chạy thử".
    fb[0 * W + 0] = 0xFF0000;
    fb[0 * W + 1] = 0x00FF00;
    fb[0 * W + 2] = 0x0000FF;

    // TODO 1: tô nền 0x003366 cho cả W * H điểm
    // TODO 2: đường ngang trắng tại y = 100, đường dọc trắng tại x = 160
    // TODO 3: điểm đỏ tại (10, 10)
    serial_print("GFX OK\n");
    halt();
}

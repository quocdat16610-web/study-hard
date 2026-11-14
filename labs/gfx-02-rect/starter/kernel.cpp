#include "gfx.h"

static volatile u32 *fb;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    // TODO: cắt hình về phần nằm trong màn hình trước khi tô
    for (int py = y; py < y + h; py++) {
        for (int px = x; px < x + w; px++) fb[py * W + px] = color;
    }
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    fill_rect(300, 20, 50, 30, 0xFFFF00);  // tràn mép phải: xem nó hiện ở đâu, rồi sửa fill_rect
    // TODO: vẽ thanh tác vụ, cửa sổ, thanh tiêu đề và hai hình tràn mép theo đề (bỏ hình mẫu ở trên)
    serial_print("GFX OK\n");
    halt();
}

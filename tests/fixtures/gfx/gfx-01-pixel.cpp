#include "gfx.h"

extern "C" void kmain() {
    volatile u32 *fb = fb_init();
    if (!fb) {
        serial_print("NO FRAMEBUFFER\n");
        halt();
    }
    for (int i = 0; i < W * H; i++) fb[i] = 0x003366;
    for (int x = 0; x < W; x++) fb[100 * W + x] = 0xFFFFFF;
    for (int y = 0; y < H; y++) fb[y * W + 160] = 0xFFFFFF;
    fb[10 * W + 10] = 0xFF0000;
    serial_print("GFX OK\n");
    halt();
}

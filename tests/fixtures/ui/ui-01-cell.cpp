#include "ui.h"

extern "C" void kmain() {
    const u8 desk = attr(WHITE, BLUE);
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', desk);
    const u8 hi = attr(YELLOW, BLUE);
    VGA[12 * COLS + 39] = cell('O', hi);
    VGA[12 * COLS + 40] = cell('S', hi);
    serial_print("UI OK\n");
    halt();
}

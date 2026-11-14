#include "ui.h"

struct Window {
    int r, c, h, w;
    const char *title;
    char text[24];  // nội dung dòng đầu của cửa sổ
    int n;          // số ký tự đang có trong text
};

static Window wins[2] = {{2, 5, 10, 30, " A ", {}, 0}, {6, 20, 10, 30, " B ", {}, 0}};
static const u8 BODY = attr(BLACK, LIGHT_GREY), ACTIVE = attr(WHITE, BLUE), DESK = attr(LIGHT_GREY, CYAN);

static void put(int r, int c, char ch, u8 a) { VGA[r * COLS + c] = cell(ch, a); }

static void draw(const Window &win, bool focused) {
    for (int y = 0; y < win.h; y++) {
        for (int x = 0; x < win.w; x++) {
            const bool top = y == 0, bottom = y == win.h - 1, left = x == 0, right = x == win.w - 1;
            char ch = ' ';
            if (top && left) ch = BOX_TL;
            else if (top && right) ch = BOX_TR;
            else if (bottom && left) ch = BOX_BL;
            else if (bottom && right) ch = BOX_BR;
            else if (top || bottom) ch = BOX_H;
            else if (left || right) ch = BOX_V;
            put(win.r + y, win.c + x, ch, top && focused ? ACTIVE : BODY);
        }
    }
    for (int i = 0; win.title[i]; i++) put(win.r, win.c + 2 + i, win.title[i], focused ? ACTIVE : BODY);
    for (int i = 0; i < win.n; i++) put(win.r + 1, win.c + 1 + i, win.text[i], BODY);
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', DESK);
    draw(wins[0], true);
    draw(wins[1], false);  // B đang đè lên A dù A mới là cửa sổ có focus: thứ tự vẽ sai
    for (;;) {
        const u8 sc = kbd_scancode();
        // TODO: KEY_TAB đổi focus; ký tự in được thêm vào wins[focus].text; vẽ lại từ sau ra trước
        (void)sc;
    }
}

"""Generate the "Đồ hoạ điểm ảnh" track: labs/gfx-0N-*/{lab.json, lesson.md, starter/, scaffold/}.

Run from anywhere: python3 tools/make_gfx_track.py
"""
import json
import shutil
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
BOOT = (repo / "tests/fixtures/toy-hello/boot.S").read_text()
TRACK = "Đồ hoạ điểm ảnh"
W = {"compile": 10, "static": 10, "dynamic": 80}
MODE = {"id": "mode", "points": 10, "expect": {"size": [320, 200], "serial": "GFX OK"},
        "concept": "lúc mới boot card VGA ở text mode; kernel phải tự bật chế độ đồ hoạ rồi mới có framebuffer để vẽ"}

# ---- 5x7 bitmap font (drawn for this course) -------------------------------------------------
GLYPHS = {
    " ": "..... ..... ..... ..... ..... ..... .....",
    "A": ".XXX. X...X X...X XXXXX X...X X...X X...X", "B": "XXXX. X...X X...X XXXX. X...X X...X XXXX.",
    "C": ".XXX. X...X X.... X.... X.... X...X .XXX.", "D": "XXXX. X...X X...X X...X X...X X...X XXXX.",
    "E": "XXXXX X.... X.... XXXX. X.... X.... XXXXX", "F": "XXXXX X.... X.... XXXX. X.... X.... X....",
    "G": ".XXX. X...X X.... X.XXX X...X X...X .XXXX", "H": "X...X X...X X...X XXXXX X...X X...X X...X",
    "I": ".XXX. ..X.. ..X.. ..X.. ..X.. ..X.. .XXX.", "J": "..XXX ...X. ...X. ...X. ...X. X..X. .XX..",
    "K": "X...X X..X. X.X.. XX... X.X.. X..X. X...X", "L": "X.... X.... X.... X.... X.... X.... XXXXX",
    "M": "X...X XX.XX X.X.X X.X.X X...X X...X X...X", "N": "X...X XX..X X.X.X X..XX X...X X...X X...X",
    "O": ".XXX. X...X X...X X...X X...X X...X .XXX.", "P": "XXXX. X...X X...X XXXX. X.... X.... X....",
    "Q": ".XXX. X...X X...X X...X X.X.X X..X. .XX.X", "R": "XXXX. X...X X...X XXXX. X.X.. X..X. X...X",
    "S": ".XXXX X.... X.... .XXX. ....X ....X XXXX.", "T": "XXXXX ..X.. ..X.. ..X.. ..X.. ..X.. ..X..",
    "U": "X...X X...X X...X X...X X...X X...X .XXX.", "V": "X...X X...X X...X X...X X...X .X.X. ..X..",
    "W": "X...X X...X X...X X.X.X X.X.X XX.XX X...X", "X": "X...X X...X .X.X. ..X.. .X.X. X...X X...X",
    "Y": "X...X X...X .X.X. ..X.. ..X.. ..X.. ..X..", "Z": "XXXXX ....X ...X. ..X.. .X... X.... XXXXX",
    "0": ".XXX. X...X X..XX X.X.X XX..X X...X .XXX.", "1": "..X.. .XX.. ..X.. ..X.. ..X.. ..X.. .XXX.",
    "2": ".XXX. X...X ....X ...X. ..X.. .X... XXXXX", "3": "XXXX. ....X ....X .XXX. ....X ....X XXXX.",
    "4": "...X. ..XX. .X.X. X..X. XXXXX ...X. ...X.", "5": "XXXXX X.... XXXX. ....X ....X X...X .XXX.",
    "6": ".XXX. X.... X.... XXXX. X...X X...X .XXX.", "7": "XXXXX ....X ...X. ..X.. .X... .X... .X...",
    "8": ".XXX. X...X X...X .XXX. X...X X...X .XXX.", "9": ".XXX. X...X X...X .XXXX ....X ....X .XXX.",
    ".": "..... ..... ..... ..... ..... .XX.. .XX..", ",": "..... ..... ..... ..... .XX.. ..X.. .X...",
    ":": "..... .XX.. .XX.. ..... .XX.. .XX.. .....", "!": "..X.. ..X.. ..X.. ..X.. ..X.. ..... ..X..",
    "?": ".XXX. X...X ....X ...X. ..X.. ..... ..X..", "-": "..... ..... ..... XXXXX ..... ..... .....",
    "+": "..... ..X.. ..X.. XXXXX ..X.. ..X.. .....", "=": "..... ..... XXXXX ..... XXXXX ..... .....",
    "/": "....X ....X ...X. ..X.. .X... X.... X....", "(": "...X. ..X.. .X... .X... .X... ..X.. ...X.",
    ")": ".X... ..X.. ...X. ...X. ...X. ..X.. .X...", "_": "..... ..... ..... ..... ..... ..... XXXXX",
    "<": "...X. ..X.. .X... X.... .X... ..X.. ...X.", ">": ".X... ..X.. ...X. ....X ...X. ..X.. .X...",
}
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    GLYPHS[ch.lower()] = GLYPHS[ch]
assert all(len(g.split()) == 7 and all(len(r) == 5 and set(r) <= {"X", "."} for r in g.split()) for g in GLYPHS.values())


def font_header() -> str:
    rows = []
    for code in range(128):
        g = GLYPHS.get(chr(code), GLYPHS[" "]).split()
        bits = ", ".join(f"0x{int(r.replace('X', '1').replace('.', '0'), 2):02X}" for r in g)
        name = repr(chr(code)) if 32 < code < 127 else str(code)
        rows.append(f"    {{{bits}}},  // {name}")
    return ("// Font bitmap 5x7 (chỉ đọc). FONT[mã ký tự][hàng] là 5 bit của một hàng: bit 4 (0x10) là cột trái nhất.\n"
            "// Chữ thường dùng chung hình với chữ hoa; ký tự không có hình sẽ để trống.\n"
            "#pragma once\n\nconstexpr int FONT_W = 5;        // chiều rộng một ký tự\n"
            "constexpr int FONT_H = 7;        // chiều cao một ký tự\n"
            "constexpr int FONT_ADVANCE = 6;  // khoảng cách giữa hai ký tự liền nhau (5 + 1 cột trống)\n\n"
            "inline constexpr unsigned char FONT[128][7] = {\n" + "\n".join(rows) + "\n};\n")


def text_bitmap(x: int, y: int, text: str, on: str, off: str) -> dict:
    """Exact expected pixels of `text` drawn at (x, y): every on and off pixel of its bounding box."""
    rows = ["".join(GLYPHS[ch].split()[r] + "." for ch in text) for r in range(7)]
    return {"x": x, "y": y, "rows": rows, "on": on, "off": off}


def px(*points):
    return [{"x": x, "y": y, "rgb": c} for x, y, c in points]


def rect(x, y, w, h, c):
    return {"x": x, "y": y, "w": w, "h": h, "rgb": c}


COMMON = '''#include "gfx.h"
'''
FILL_RECT = '''static void fill_rect(int x, int y, int w, int h, u32 color) {
    const int x0 = x < 0 ? 0 : x, y0 = y < 0 ? 0 : y;
    const int x1 = x + w > W ? W : x + w, y1 = y + h > H ? H : y + h;
    for (int py = y0; py < y1; py++) {
        for (int px = x0; px < x1; px++) fb[py * W + px] = color;
    }
}
'''
DRAW_TEXT = '''static void draw_text(int x, int y, const char *s, u32 color) {
    for (; *s; s++, x += FONT_ADVANCE) {
        const unsigned char *glyph = FONT[static_cast<u8>(*s) & 127];
        for (int row = 0; row < FONT_H; row++) {
            for (int col = 0; col < FONT_W; col++) {
                if (glyph[row] & (0x10 >> col)) fill_rect(x + col, y + row, 1, 1, color);
            }
        }
    }
}
'''

LABS = {}

# ------------------------------------------------------------------ 1
LABS["gfx-01-pixel"] = dict(
    title="1. Framebuffer và điểm ảnh",
    statement="Bật chế độ đồ hoạ 320x200, tô nền màu `0x003366`, vẽ một đường ngang trắng ở y = 100, một đường dọc trắng ở x = 160 và một điểm đỏ (`0xFF0000`) tại (10, 10). Gửi `GFX OK` ra serial.",
    lesson="""# Từ ô ký tự sang điểm ảnh

Ở text mode, card màn hình vẽ chữ giúp bạn. Ở chế độ đồ hoạ thì không: màn hình là một mảng **điểm ảnh**, mọi thứ — chữ, cửa sổ, con trỏ chuột — đều do kernel tự tô từng điểm.

Vùng nhớ chứa các điểm ảnh gọi là **framebuffer**. Với chế độ 320x200, 32 bit mỗi điểm:

- Điểm ảnh (x, y) nằm ở `fb[y * W + x]`. Gốc toạ độ ở góc trên trái, y tăng xuống dưới.
- Mỗi điểm là một số `0x00RRGGBB`: `0xFF0000` là đỏ, `0x00FF00` xanh lá, `0xFFFFFF` trắng.

# Bật chế độ đồ hoạ

`fb_init()` trong `gfx.h` làm hai việc, hãy mở tab `gfx.h` để đọc:

1. Ghi độ phân giải vào các thanh ghi của card (giao diện Bochs VBE, cổng 0x1CE/0x1CF).
2. Hỏi bus PCI xem card đặt framebuffer ở địa chỉ nào (thanh ghi BAR0).

Địa chỉ đó không cố định: firmware cấp phát lúc khởi động, nên kernel phải hỏi chứ không được viết cứng.

# Việc cần làm

1. Tô cả 64000 điểm bằng màu nền.
2. Đường ngang là 320 điểm có cùng y; đường dọc là 200 điểm có cùng x.
3. Một điểm đỏ tại (10, 10).
4. `serial_print("GFX OK\\n")`.

Đường chéo thì sao? Thử vẽ thêm sau khi xong bài: nó là lý do các thuật toán vẽ đường thẳng ra đời.
""",
    starter=COMMON + '''
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
    serial_print("GFX OK\\n");
    halt();
}
''',
    tests=[
        MODE,
        {"id": "background", "points": 25, "expect": {"pixels": px((0, 0, "003366"), (319, 199, "003366"), (50, 50, "003366"), (300, 150, "003366"))},
         "concept": "framebuffer là mảng một chiều: W * H phần tử, mỗi phần tử một điểm ảnh"},
        {"id": "horizontal", "points": 25, "expect": {"rects": [rect(0, 100, 160, 1, "ffffff"), rect(161, 100, 159, 1, "ffffff")], "pixels": px((5, 99, "003366"), (5, 101, "003366"))},
         "concept": "điểm (x, y) ở chỉ số y * W + x; một đường ngang là dãy chỉ số liên tiếp"},
        {"id": "vertical", "points": 25, "expect": {"rects": [rect(160, 0, 1, 200, "ffffff")], "pixels": px((159, 5, "003366"), (161, 5, "003366"))},
         "concept": "đi xuống một hàng là cộng thêm W vào chỉ số"},
        {"id": "pixel", "points": 15, "expect": {"pixels": px((10, 10, "ff0000"), (11, 10, "003366"), (10, 11, "003366"), (9, 10, "003366"))},
         "concept": "màu 32 bit dạng 0x00RRGGBB: mỗi kênh đỏ, lục, lam chiếm 8 bit"},
    ])

# ------------------------------------------------------------------ 2
LABS["gfx-02-rect"] = dict(
    title="2. Hình chữ nhật và cắt xén (clipping)",
    statement="Viết `fill_rect(x, y, w, h, màu)` an toàn với mọi toạ độ, kể cả khi hình nằm một phần ngoài màn hình. Vẽ: nền `0x008080`; thanh tác vụ `(0, 184, 320, 16)` màu `0xC0C0C0`; thân cửa sổ `(40, 30, 200, 120)` trắng; thanh tiêu đề `(40, 30, 200, 14)` màu `0x000080`; rồi hai hình tràn mép: `(300, -10, 50, 30)` vàng `0xFFFF00` và `(-20, 170, 40, 60)` hồng `0xFF00FF`.",
    lesson="""# Hình chữ nhật: viên gạch của mọi giao diện

Nền desktop, thanh tác vụ, cửa sổ, nút bấm — tất cả đều là hình chữ nhật tô màu. Một hàm `fill_rect` tốt là nền móng của cả hệ thống đồ hoạ.

Phiên bản ngây thơ là hai vòng lặp lồng nhau. Nó sai ngay khi hình chạm mép màn hình.

# Vì sao phải cắt xén

Framebuffer là mảng một chiều. Nếu vẽ điểm có x = 330 ở hàng y, chỉ số `y * W + 330` vẫn hợp lệ — nhưng nó là điểm x = 10 của hàng **y + 1**. Hình tràn mép phải sẽ "mọc" lại ở mép trái. Với y âm hoặc y >= H thì tệ hơn: bạn ghi ra ngoài framebuffer, vào vùng nhớ của thứ khác.

Cửa sổ kéo ra ngoài mép màn hình là chuyện bình thường, nên hàm vẽ phải tự **cắt** hình về phần giao với màn hình trước khi tô:

```
x0 = max(x, 0)          y0 = max(y, 0)
x1 = min(x + w, W)      y1 = min(y + h, H)
tô các điểm x0 <= px < x1, y0 <= py < y1
```

Nếu x0 >= x1 hoặc y0 >= y1 thì hình nằm hẳn ngoài màn hình và vòng lặp tự không chạy.

# Thứ tự vẽ

Hình vẽ sau đè lên hình vẽ trước. Vẽ đúng thứ tự trong đề: nền, thanh tác vụ, thân cửa sổ, thanh tiêu đề, rồi hai hình tràn mép.

# Việc cần làm

Mã khởi đầu có `fill_rect` chưa cắt xén. Hãy sửa nó và vẽ đủ cảnh theo đề. Chạy thử trước khi sửa để tận mắt thấy hình vàng mọc lại ở mép trái.
""",
    starter=COMMON + '''
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
    serial_print("GFX OK\\n");
    halt();
}
''',
    tests=[
        MODE,
        {"id": "scene", "points": 30, "expect": {"rects": [rect(20, 184, 280, 16, "c0c0c0"), rect(40, 44, 200, 106, "ffffff"), rect(40, 30, 200, 14, "000080")],
                                                  "pixels": px((10, 100, "008080"), (280, 100, "008080"), (39, 30, "008080"), (240, 30, "008080"), (100, 150, "008080"))},
         "concept": "hình vẽ sau đè lên hình vẽ trước; mép phải của hình rộng w bắt đầu ở x là x + w - 1"},
        {"id": "clip-right-top", "points": 30, "expect": {"rects": [rect(300, 0, 20, 20, "ffff00")], "pixels": px((299, 5, "008080"), (5, 5, "008080"), (5, 15, "008080"), (310, 20, "008080"))},
         "concept": "không cắt xén thì điểm có x >= W rơi sang đầu hàng kế tiếp, vì framebuffer là mảng một chiều"},
        {"id": "clip-left-bottom", "points": 30, "expect": {"rects": [rect(0, 170, 20, 30, "ff00ff")], "pixels": px((20, 175, "008080"), (310, 169, "008080"), (310, 175, "008080"))},
         "concept": "toạ độ âm phải được nâng về 0; y vượt H nghĩa là ghi ra ngoài vùng nhớ của màn hình"},
    ])

# ------------------------------------------------------------------ 3
LABS["gfx-03-text"] = dict(
    title="3. Font bitmap: tự vẽ chữ",
    statement="Viết `draw_char` và `draw_text` dùng font 5x7 trong `font.h`. Tô nền `0x000080`, in `HELLO OS` màu trắng tại (8, 8), rồi in `320X200\\nPIXELS` màu vàng `0xFFFF00` tại (8, 24). Ký tự xuống dòng đưa về cột x ban đầu và xuống `FONT_H + 2` điểm.",
    lesson="""# Chữ cũng chỉ là điểm ảnh

Ở chế độ đồ hoạ không còn bảng ký tự của card VGA. Muốn có chữ, kernel cần một **font bitmap**: mỗi ký tự là một bức tranh nhỏ, mỗi bit cho biết một điểm có được tô hay không.

Font của bài này rộng 5, cao 7. Chữ `H`:

```
X...X   -> 0x11
X...X   -> 0x11
X...X   -> 0x11
XXXXX   -> 0x1F
X...X   -> 0x11
X...X   -> 0x11
X...X   -> 0x11
```

`FONT[mã ký tự][hàng]` là một byte, trong đó bit 4 (`0x10`) là cột trái nhất. Cột `col` của một hàng được tô khi `hàng & (0x10 >> col)` khác 0. Mở tab `font.h` để xem toàn bộ.

# Vẽ một ký tự

Duyệt 7 hàng x 5 cột; với mỗi bit bật, tô điểm (x + col, y + row). Bit tắt thì **không tô gì** — nhờ vậy chữ nằm đè lên bất kỳ nền nào (nền trong suốt).

# Vẽ một chuỗi

Sau mỗi ký tự, dịch sang phải `FONT_ADVANCE` = 6 điểm (5 cột chữ + 1 cột trống). Gặp `\\n`: quay về x ban đầu và tăng y thêm `FONT_H + 2`.

# Việc cần làm

Mã khởi đầu vẽ mỗi ký tự thành một khối đặc. Hãy hoàn thiện `draw_char` để dùng dữ liệu font, và thêm xử lý `\\n` vào `draw_text`.

Tại sao font có sẵn chỉ gồm chữ hoa? Vì vẽ font là việc thủ công: mỗi ký tự là 7 con số. Thử sửa một ký tự của riêng bạn bằng cách vẽ nó bằng các lệnh `put_pixel`.
""",
    starter='''#include "font.h"
#include "gfx.h"

static volatile u32 *fb;

static void put_pixel(int x, int y, u32 color) {
    if (x >= 0 && x < W && y >= 0 && y < H) fb[y * W + x] = color;
}

static void draw_char(int x, int y, char ch, u32 color) {
    const unsigned char *glyph = FONT[static_cast<u8>(ch) & 127];
    for (int row = 0; row < FONT_H; row++) {
        for (int col = 0; col < FONT_W; col++) {
            // TODO: chỉ tô khi bit tương ứng của glyph[row] bật (hiện đang tô cả khối)
            if (glyph[row] || true) put_pixel(x + col, y + row, color);
        }
    }
}

static void draw_text(int x, int y, const char *s, u32 color) {
    // TODO: xử lý '\\n' (về cột x ban đầu, xuống FONT_H + 2 điểm)
    for (; *s; s++, x += FONT_ADVANCE) draw_char(x, y, *s, color);
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    for (int i = 0; i < W * H; i++) fb[i] = 0x000080;
    draw_text(8, 8, "HELLO OS", 0xFFFFFF);
    draw_text(8, 24, "320X200\\nPIXELS", 0xFFFF00);
    serial_print("GFX OK\\n");
    halt();
}
''',
    tests=[
        MODE,
        {"id": "glyph", "points": 30, "expect": {"bitmaps": [text_bitmap(8, 8, "H", "ffffff", "000080")]},
         "concept": "mỗi hàng của ký tự là một byte; bit 4 là cột trái nhất, nên kiểm tra bằng 0x10 >> col"},
        {"id": "text", "points": 30, "expect": {"bitmaps": [text_bitmap(8, 8, "HELLO OS", "ffffff", "000080")], "pixels": px((8, 7, "000080"), (8, 15, "000080"), (56, 10, "000080"))},
         "concept": "bit tắt không được tô: chữ có nền trong suốt; mỗi ký tự cách nhau FONT_ADVANCE điểm"},
        {"id": "newline", "points": 30, "expect": {"bitmaps": [text_bitmap(8, 24, "320X200", "ffff00", "000080"), text_bitmap(8, 33, "PIXELS", "ffff00", "000080")], "pixels": px((50, 24, "000080"), (50, 33, "000080"))},
         "concept": "xuống dòng là việc của hàm vẽ chuỗi: đặt lại x và cộng chiều cao dòng vào y"},
    ])

# ------------------------------------------------------------------ 4
LABS["gfx-04-window"] = dict(
    title="4. Cửa sổ đồ hoạ",
    statement="Viết `draw_window(x, y, w, h, tiêu_đề, active)`: viền đen 1 điểm; thân `0xC0C0C0`; thanh tiêu đề cao 12 điểm ngay trong viền, màu `0x000080` khi active và `0x808080` khi không; tiêu đề trắng tại (x + 4, y + 3); nút đóng đỏ 8x8 tại (x + w - 11, y + 3). Trên nền `0x008080`, vẽ cửa sổ `FILES` active tại (30, 20) cỡ 180x100, chữ đen `3 ITEMS` tại (36, 40), và cửa sổ `NOTES` không active tại (120, 130) cỡ 150x60.",
    lesson="""# Ghép các viên gạch

Bạn đã có hình chữ nhật và chữ. Một cửa sổ là sự xếp chồng có thứ tự của chúng:

```
1. viền:          fill_rect(x, y, w, h, đen)
2. thân:          fill_rect(x + 1, y + 1, w - 2, h - 2, xám)
3. thanh tiêu đề: fill_rect(x + 1, y + 1, w - 2, 12, màu theo trạng thái)
4. tiêu đề:       draw_text(x + 4, y + 3, ...)
5. nút đóng:      fill_rect(x + w - 11, y + 3, 8, 8, đỏ)
```

Viền 1 điểm xuất hiện "miễn phí": vẽ hình đen lớn rồi đè hình xám nhỏ hơn mỗi cạnh 1 điểm lên trên. Đây là mẹo quen thuộc — vẽ nhiều lớp đơn giản thay vì tính từng cạnh.

# Toạ độ tương đối

Mọi thành phần được tính từ (x, y) của cửa sổ. Nhờ vậy cùng một hàm vẽ được cửa sổ ở bất kỳ đâu, và di chuyển cửa sổ chỉ là đổi hai con số.

# Trạng thái hiển thị

Tham số `active` chưa làm gì ngoài đổi màu thanh tiêu đề. Nhưng đó chính là cách giao diện "nói" với người dùng cửa sổ nào đang nhận bàn phím — bài 6 sẽ dùng nó thật.

# Việc cần làm

`fill_rect` (đã cắt xén) và `draw_text` được cho sẵn. Mã khởi đầu mới vẽ thân cửa sổ. Hãy hoàn thiện `draw_window` đúng kích thước và màu trong đề.
""",
    starter='''#include "font.h"
#include "gfx.h"

static volatile u32 *fb;

''' + FILL_RECT + "\n" + DRAW_TEXT + '''
static void draw_window(int x, int y, int w, int h, const char *title, bool active) {
    fill_rect(x, y, w, h, 0xFFFFFF);  // tạm: mới chỉ là một hình trắng
    // TODO: viền đen 1 điểm, thân 0xC0C0C0, thanh tiêu đề (màu theo active), tiêu đề trắng, nút đóng đỏ
    draw_text(x + 4, y + 3, title, active ? 0x000000 : 0x404040);
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    draw_window(30, 20, 180, 100, "FILES", true);
    draw_text(36, 40, "3 ITEMS", 0x000000);
    draw_window(120, 130, 150, 60, "NOTES", false);
    serial_print("GFX OK\\n");
    halt();
}
''',
    tests=[
        MODE,
        {"id": "border", "points": 20, "expect": {"rects": [rect(30, 20, 180, 1, "000000"), rect(30, 119, 180, 1, "000000"), rect(30, 20, 1, 100, "000000"), rect(209, 20, 1, 100, "000000")],
                                                   "pixels": px((29, 50, "008080"), (210, 50, "008080"), (100, 19, "008080"), (100, 120, "008080"))},
         "concept": "viền 1 điểm = hình đen lớn bị hình nhỏ hơn mỗi cạnh 1 điểm đè lên"},
        {"id": "title-bar", "points": 20, "expect": {"rects": [rect(70, 21, 120, 12, "000080"), rect(31, 21, 3, 12, "000080")], "bitmaps": [text_bitmap(34, 23, "FILES", "ffffff", "000080")],
                                                      "pixels": px((100, 33, "c0c0c0"))},
         "concept": "thanh tiêu đề nằm trong viền: bắt đầu ở (x + 1, y + 1), rộng w - 2"},
        {"id": "close-button", "points": 15, "expect": {"rects": [rect(199, 23, 8, 8, "ff0000")], "pixels": px((198, 26, "000080"), (207, 26, "000080"), (203, 22, "000080"), (203, 31, "000080"))},
         "concept": "vị trí tính từ mép phải của cửa sổ (x + w - 11) để nút luôn bám góc khi cửa sổ đổi kích thước"},
        {"id": "body", "points": 15, "expect": {"rects": [rect(31, 60, 178, 59, "c0c0c0")], "bitmaps": [text_bitmap(36, 40, "3 ITEMS", "000000", "c0c0c0")]},
         "concept": "nội dung cửa sổ được vẽ sau khung, bằng toạ độ tính từ gốc cửa sổ"},
        {"id": "inactive", "points": 20, "expect": {"rects": [rect(160, 131, 90, 12, "808080"), rect(259, 133, 8, 8, "ff0000"), rect(120, 130, 150, 1, "000000")],
                                                     "bitmaps": [text_bitmap(124, 133, "NOTES", "ffffff", "808080")]},
         "concept": "cùng một hàm vẽ mọi cửa sổ; trạng thái active chỉ đổi màu thanh tiêu đề"},
    ])

# ------------------------------------------------------------------ 5
CURSOR_SCRIPT = [{"wait": 2}, {"snap": "start"}, {"mouse": [-30, -20]}, {"wait": 0.5}, {"snap": "moved"},
                 {"mouse": [50, 60]}, {"wait": 0.5}, {"snap": "restored"}, {"mouse": [300, 300]}, {"wait": 0.8}]
LABS["gfx-05-mouse"] = dict(
    title="5. Chuột PS/2 và con trỏ",
    statement="Vẽ nền `0x008080` và một hình đỏ `(100, 60, 60, 40)`. Hiển thị con trỏ là hình vuông trắng 5x5 có góc trên trái tại (160, 100). Đọc gói tin chuột PS/2 để di chuyển con trỏ; khi con trỏ rời đi, hình nền bên dưới phải được khôi phục. Con trỏ luôn nằm trọn trong màn hình.",
    script=CURSOR_SCRIPT,
    lesson="""# Chuột nói gì với kernel

Chuột không biết nó đang ở đâu trên màn hình. Nó chỉ báo **độ dịch chuyển** kể từ lần trước, trong gói 3 byte:

```
byte 0:  bit 0 = nút trái   bit 1 = nút phải   bit 2 = nút giữa
         bit 3 = luôn là 1
         bit 4 = dấu của dx  bit 5 = dấu của dy
byte 1:  dx (8 bit thấp)
byte 2:  dy (8 bit thấp)
```

- dx, dy là số có dấu 9 bit: nếu bit dấu bật thì giá trị thật là `byte - 256`.
- **dy dương nghĩa là chuột đi lên**, ngược với trục y của màn hình. Vị trí mới là `cy - dy`.

Vị trí con trỏ là thứ kernel tự giữ (`cx`, `cy`) và tự cộng dồn.

# Đọc gói tin

`gfx.h` cho sẵn `mouse_init()` (bật chuột) và `mouse_poll(byte)` (lấy một byte của chuột nếu có). Việc của bạn là gom đủ 3 byte.

Nếu lỡ mất một byte, mọi gói sau đó sẽ lệch. Cách đồng bộ lại: byte đầu của gói luôn có bit 3 bật; khi đang chờ byte đầu mà gặp byte không có bit 3 thì bỏ qua.

# Con trỏ không được phá hình nền

Vẽ con trỏ là ghi đè lên framebuffer. Khi nó di chuyển, chỗ cũ phải trở lại như trước:

```
ẩn con trỏ:   chép saved[] trả lại màn hình
đổi vị trí:   cx, cy (đã chặn trong màn hình)
hiện con trỏ: chép vùng 5x5 mới vào saved[], rồi tô trắng
```

Đọc lại framebuffer (`fb[...]` ở vế phải) là hợp lệ. Bài test kéo con trỏ qua hình đỏ rồi đi tiếp: nếu không lưu nền, hình đỏ sẽ bị thủng một lỗ màu nền.

# Chặn biên

Con trỏ 5x5 nằm trọn trong màn hình khi `0 <= cx <= W - 5` và `0 <= cy <= H - 5`.

# Việc cần làm

Mã khởi đầu đã vẽ cảnh và con trỏ đứng yên. Hãy gom gói tin, tính dx/dy, và di chuyển con trỏ có lưu/khôi phục nền.

Dùng **Chạy trực tiếp** rồi rê chuột trên màn hình kernel để thử.
""",
    starter=COMMON + '''
static volatile u32 *fb;
static const int CURSOR = 5;
static int cx = 160, cy = 100;

static void fill_rect(int x, int y, int w, int h, u32 color) {
    for (int py = y; py < y + h; py++) {
        for (int px = x; px < x + w; px++) fb[py * W + px] = color;
    }
}

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    fill_rect(0, 0, W, H, 0x008080);
    fill_rect(100, 60, 60, 40, 0xFF0000);
    mouse_init();
    fill_rect(cx, cy, CURSOR, CURSOR, 0xFFFFFF);
    serial_print("GFX OK\\n");
    for (;;) {
        u8 byte;
        if (!mouse_poll(byte)) continue;
        // TODO: gom 3 byte thành một gói (đồng bộ bằng bit 3 của byte đầu), tính dx và dy có dấu,
        //       ẩn con trỏ (khôi phục nền), cập nhật cx/cy có chặn biên, hiện con trỏ (lưu nền mới)
    }
}
''',
    tests=[
        {"id": "start", "points": 15, "expect": {"at": "start", "size": [320, 200], "rects": [rect(160, 100, 5, 5, "ffffff"), rect(100, 60, 60, 40, "ff0000")], "pixels": px((165, 100, "008080"), (160, 105, "008080"))},
         "concept": "con trỏ chỉ là một hình nhỏ vẽ sau cùng, tại vị trí kernel tự ghi nhớ"},
        {"id": "move", "points": 30, "expect": {"at": "moved", "rects": [rect(130, 80, 5, 5, "ffffff")], "pixels": px((162, 102, "008080"), (129, 80, "ff0000"), (135, 80, "ff0000"))},
         "concept": "gói tin chứa độ dịch chuyển có dấu 9 bit; dy dương là đi lên nên phải trừ vào toạ độ y của màn hình"},
        {"id": "restore", "points": 30, "expect": {"at": "restored", "rects": [rect(180, 140, 5, 5, "ffffff"), rect(100, 60, 60, 40, "ff0000")], "pixels": px((162, 102, "008080"))},
         "concept": "trước khi vẽ con trỏ phải lưu vùng nền nó che, để trả lại khi con trỏ rời đi"},
        {"id": "clamp", "points": 25, "expect": {"rects": [rect(315, 195, 5, 5, "ffffff")], "pixels": px((314, 195, "008080"), (315, 194, "008080"), (0, 0, "008080"), (182, 142, "008080"))},
         "concept": "toạ độ con trỏ phải được chặn trong màn hình, nếu không nó vẽ ra ngoài framebuffer"},
    ])

# ------------------------------------------------------------------ 6
MOUSE_READ = '''// Gom một gói tin chuột. Trả về true khi đủ 3 byte; dx, dy theo trục màn hình (dy dương = đi xuống).
static bool mouse_read(int &dx, int &dy, bool &left) {
    static u8 packet[3];
    static int n = 0;
    u8 byte;
    if (!mouse_poll(byte)) return false;
    if (n == 0 && !(byte & 0x08)) return false;
    packet[n++] = byte;
    if (n < 3) return false;
    n = 0;
    dx = packet[1] - ((packet[0] & 0x10) ? 256 : 0);
    dy = -(packet[2] - ((packet[0] & 0x20) ? 256 : 0));
    left = packet[0] & 1;
    return true;
}
'''
DESKTOP_SCRIPT = [{"wait": 2}, {"snap": "start"}, {"mouse": [40, 20]}, {"wait": 0.3}, {"click": "left"}, {"wait": 0.5}, {"snap": "b"},
                  {"mouse": [-160, -80]}, {"wait": 0.3}, {"click": "left"}, {"wait": 0.5}, {"snap": "a"},
                  {"mouse": [90, 40]}, {"wait": 0.3}, {"click": "left"}, {"wait": 0.8}]
LABS["gfx-06-desktop"] = dict(
    title="6. Desktop: back buffer, click và thứ tự chồng",
    statement="Dựng desktop có hai cửa sổ chồng nhau: `A` tại (20, 20) và `B` tại (100, 60), mỗi cái 140x90, vẽ như bài 4. Lúc đầu A nằm trên và active. Con trỏ 5x5 trắng bắt đầu tại (160, 100) và luôn nằm trên cùng. Click trái vào cửa sổ đang nằm dưới sẽ đưa nó lên trên và thành active; click vào vùng hai cửa sổ chồng nhau thì cửa sổ đang ở trên nhận click. Mỗi khung hình phải được dựng trong back buffer rồi mới chép ra màn hình.",
    script=DESKTOP_SCRIPT,
    lesson="""# Vì sao cần back buffer

Ở bài 5, con trỏ phải tự lưu và trả lại nền. Với hai cửa sổ chồng nhau, cách đó không còn đủ: khi B nổi lên trên, phần của A bị che phải biến mất; khi A nổi lại, nó phải hiện ra nguyên vẹn. Cách đơn giản và đúng nhất là **vẽ lại cả khung hình** mỗi khi có thay đổi.

Nhưng nếu vẽ lại thẳng lên màn hình, người dùng sẽ thấy cảnh dang dở: nền vừa xoá, cửa sổ chưa kịp vẽ — màn hình nhấp nháy. Lời giải là **double buffering**:

```
back[W * H]      vùng nhớ thường, cùng kích thước màn hình
compose():
    vẽ nền, cửa sổ dưới, cửa sổ trên, con trỏ   -> tất cả vào back[]
    chép back[] sang fb[]                        -> một lần duy nhất
```

Màn hình chỉ bao giờ thấy khung hình đã hoàn chỉnh. Con trỏ không cần lưu/khôi phục nền nữa: nó chỉ là lớp vẽ sau cùng của mỗi khung.

# Thứ tự chồng (z-order)

Với hai cửa sổ, z-order chỉ là một số: `top` = chỉ số cửa sổ nằm trên. Vẽ `wins[1 - top]` trước, `wins[top]` sau (thuật toán hoạ sĩ, như bài 8 phần text mode).

# Click vào đâu? (hit testing)

Khi nút trái **vừa được nhấn** (gói này có bit nút trái, gói trước thì không), cần tìm cửa sổ dưới con trỏ. Quy tắc: hỏi theo thứ tự **từ trên xuống**.

- Điểm nằm trong cửa sổ trên: cửa sổ trên nhận, không đổi gì.
- Nếu không, và nằm trong cửa sổ dưới: đưa nó lên trên.

Hỏi sai thứ tự thì click vào vùng chồng nhau sẽ "xuyên" qua cửa sổ trên — một lỗi giao diện rất khó chịu.

Chỉ phản ứng ở **cạnh lên** của nút (từ nhả sang nhấn). Nếu phản ứng mỗi gói tin có nút đang giữ, một lần click sẽ bị xử lý nhiều lần.

# Việc cần làm

Mã khởi đầu vẽ thẳng lên màn hình một lần (sai thứ tự chồng) và để con trỏ lại vệt khi di chuyển. `mouse_read` đã gom gói tin cho bạn. Hãy:

1. Chuyển các hàm vẽ sang ghi vào `back[]`, viết `compose()`.
2. Vẽ đúng z-order theo `top`, con trỏ sau cùng.
3. Xử lý click theo quy tắc hit testing ở trên.

Dùng **Chạy trực tiếp**: rê chuột và click vào các cửa sổ trên màn hình kernel.
""",
    starter='''#include "font.h"
#include "gfx.h"

struct Window {
    int x, y, w, h;
    const char *title;
};

static volatile u32 *fb;
static Window wins[2] = {{20, 20, 140, 90, "A"}, {100, 60, 140, 90, "B"}};
static int cx = 160, cy = 100;

''' + FILL_RECT + "\n" + DRAW_TEXT + '''
static void draw_window(const Window &win, bool active) {
    fill_rect(win.x, win.y, win.w, win.h, 0x000000);
    fill_rect(win.x + 1, win.y + 1, win.w - 2, win.h - 2, 0xC0C0C0);
    fill_rect(win.x + 1, win.y + 1, win.w - 2, 12, active ? 0x000080 : 0x808080);
    draw_text(win.x + 4, win.y + 3, win.title, 0xFFFFFF);
    fill_rect(win.x + win.w - 11, win.y + 3, 8, 8, 0xFF0000);
}

''' + MOUSE_READ + '''
static int clamp(int v, int lo, int hi) { return v < lo ? lo : v > hi ? hi : v; }

extern "C" void kmain() {
    fb = fb_init();
    if (!fb) halt();
    mouse_init();
    fill_rect(0, 0, W, H, 0x008080);
    draw_window(wins[0], true);
    draw_window(wins[1], false);  // B đang đè lên A dù A mới là cửa sổ active
    serial_print("GFX OK\\n");
    for (;;) {
        int dx, dy;
        bool left;
        if (!mouse_read(dx, dy, left)) continue;
        cx = clamp(cx + dx, 0, W - 5);
        cy = clamp(cy + dy, 0, H - 5);
        // TODO: back buffer + compose(); z-order theo `top`; click trái (cạnh lên) đưa cửa sổ dưới con trỏ lên trên
        fill_rect(cx, cy, 5, 5, left ? 0xFFFF00 : 0xFFFFFF);  // vẽ thẳng lên màn hình: con trỏ để lại vệt
    }
}
''',
    tests=[
        {"id": "initial", "points": 20, "expect": {"at": "start", "size": [320, 200], "pixels": px((90, 26, "000080"), (130, 66, "c0c0c0"), (200, 66, "808080"), (5, 5, "008080"), (159, 50, "000000"), (239, 100, "000000")),
                                                   "rects": [rect(160, 100, 5, 5, "ffffff")]},
         "concept": "thuật toán hoạ sĩ: cửa sổ dưới vẽ trước, cửa sổ trên vẽ sau, con trỏ sau cùng"},
        {"id": "raise", "points": 30, "expect": {"at": "b", "pixels": px((130, 66, "000080"), (200, 66, "000080"), (90, 26, "808080"), (100, 80, "000000")), "rects": [rect(200, 120, 5, 5, "ffffff")]},
         "concept": "click vào cửa sổ nằm dưới đưa nó lên trên: z-order và trạng thái active đổi cùng lúc"},
        {"id": "restore", "points": 25, "expect": {"at": "a", "pixels": px((90, 26, "000080"), (130, 66, "c0c0c0"), (200, 66, "808080"), (202, 122, "c0c0c0")), "rects": [rect(40, 40, 5, 5, "ffffff")]},
         "concept": "dựng lại cả khung hình trong back buffer: phần từng bị che hiện lại đúng, con trỏ không để lại vệt"},
        {"id": "hit-test", "points": 25, "expect": {"pixels": px((90, 26, "000080"), (135, 66, "c0c0c0"), (200, 66, "808080"), (42, 42, "c0c0c0")), "rects": [rect(130, 80, 5, 5, "ffffff")]},
         "concept": "hit testing đi từ trên xuống: click vào vùng chồng nhau thuộc về cửa sổ đang ở trên"},
    ])

for level, (lab_id, lab) in enumerate(LABS.items(), 1):
    d = repo / "labs" / lab_id
    for sub in ("starter", "scaffold"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    spec = {"mode": "toy", "template": "toy-gfx", "track": TRACK, "level": level, "title": lab["title"],
            "statement": lab["statement"], "files": {"required": ["kernel.cpp"], "only": ["kernel.cpp"], "max_bytes": 32768},
            "weights": W, "penalties": {"reset": 30, "bad_image": 100}}
    if "script" in lab:
        spec["script"] = lab["script"]
    spec["tests"] = lab["tests"]
    (d / "lab.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n")
    (d / "lesson.md").write_text(lab["lesson"])
    (d / "starter/kernel.cpp").write_text(lab["starter"])
    (d / "scaffold/boot.S").write_text(BOOT)
    shutil.copyfile(Path(__file__).with_name("gfx.h"), d / "scaffold/gfx.h")
    if "font.h" in lab["starter"]:
        (d / "scaffold/font.h").write_text(font_header())
print(len(LABS), "labs written")

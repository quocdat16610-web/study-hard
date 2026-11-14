"""Generate the "Giao diện OS" track: labs/ui-0N-*/{lab.json, lesson.md, starter/, scaffold/}."""
import json
import shutil
import sys
from pathlib import Path

repo = Path(__file__).resolve().parent.parent
ui_h = Path(__file__).with_name("ui.h")
BOOT = (repo / "tests/fixtures/toy-hello/boot.S").read_text()
TRACK = "Giao diện OS (text mode)"
W = {"compile": 10, "static": 10, "dynamic": 80}
BOOTED = {"id": "boots", "points": 10, "expect": {"serial": "UI OK"},
          "concept": "serial là kênh gỡ lỗi đầu tiên của mọi kernel: nó hoạt động trước cả khi màn hình được thiết lập"}


def cells(*c):
    return [dict(zip(("row", "col"), x[:2])) | x[2] for x in c]


LABS = {}

# ------------------------------------------------------------------ 1
LABS["ui-01-cell"] = dict(
    title="1. Ô ký tự và màu",
    statement="Tô cả màn hình nền xanh dương (thuộc tính 0x1F), rồi in chữ `OS` màu vàng trên nền xanh (0x1E) tại hàng 12, cột 39. Gửi `UI OK` ra serial khi xong.",
    lesson="""# Màn hình là một mảng

Ở text mode, card VGA hiển thị 25 hàng x 80 cột ký tự. Toàn bộ màn hình chỉ là một vùng nhớ bắt đầu tại địa chỉ vật lý `0xB8000`: ghi vào đó là chữ hiện ra, không cần gọi hàm nào của hệ điều hành — vì chính bạn đang viết hệ điều hành.

Mỗi ô chiếm 2 byte:

```
bit 15..12   bit 11..8   bit 7..0
 màu nền     màu chữ     mã ký tự (CP437)
```

- Ô ở (hàng, cột) có chỉ số `hàng * 80 + cột`.
- Thuộc tính `0x1F` nghĩa là nền 1 (xanh dương), chữ F (trắng).
- `ui.h` có sẵn `VGA`, `attr(chữ, nền)` và `cell(ký tự, thuộc tính)`.

# Việc cần làm

1. Tô 2000 ô bằng dấu cách với thuộc tính 0x1F. Lúc kernel bắt đầu chạy, màn hình còn chữ của BIOS; "xoá màn hình" chính là ghi đè toàn bộ.
2. Ghi `O` và `S` vào hàng 12, cột 39 và 40 với thuộc tính 0x1E.
3. Gọi `serial_print("UI OK\\n")`.

Bấm **Chạy thử** sau mỗi thay đổi để thấy màn hình đổi theo.
""",
    starter="""#include "ui.h"

extern "C" void kmain() {
    // Một ô mẫu: dấu '?' trắng trên nền đỏ ở góc trên trái. Thử đổi ký tự, màu, vị trí rồi bấm "Chạy thử".
    VGA[0] = cell('?', attr(WHITE, RED));

    // TODO 1: tô toàn màn hình bằng dấu cách, thuộc tính attr(WHITE, BLUE)
    // TODO 2: in "OS" màu YELLOW trên nền BLUE tại hàng 12, cột 39
    // TODO 3: serial_print("UI OK\\n");
    halt();
}
""",
    tests=[
        BOOTED,
        {"id": "background", "points": 40, "expect": {"cells": cells((0, 0, {"len": 80, "attr": "1f"}), (24, 0, {"len": 80, "attr": "1f"}), (12, 0, {"len": 39, "attr": "1f"}))},
         "concept": "xoá màn hình = ghi đè cả 2000 ô; byte thuộc tính quyết định màu nền kể cả khi ký tự là dấu cách"},
        {"id": "text", "points": 50, "expect": {"cells": cells((12, 39, {"text": "OS", "attr": "1e"}))},
         "concept": "ô (hàng, cột) nằm ở chỉ số hàng * 80 + cột; mỗi ô = (thuộc tính << 8) | ký tự"},
    ])

# ------------------------------------------------------------------ 2
LABS["ui-02-print"] = dict(
    title="2. Con trỏ, xuống dòng và in chuỗi",
    statement="Viết `putc` có con trỏ (hàng, cột): xử lý `\\n` và tự xuống dòng khi hết 80 cột. Xoá màn hình, in `Line 1`, `Line 2` trên hai dòng, rồi in 100 chữ `x` liên tiếp.",
    lesson="""# Từ ô nhớ tới "in ra màn hình"

`printf` không tồn tại trong kernel. Thứ gần nhất bạn có là một hàm `putc` tự viết, nhớ vị trí sẽ ghi tiếp theo — gọi là con trỏ (cursor).

Con trỏ chỉ là hai số nguyên `row`, `col`. Mỗi lần in một ký tự:

- Ký tự thường: ghi vào ô (row, col) rồi tăng `col`.
- `\\n`: không ghi gì, đưa `col` về 0 và tăng `row`.
- Khi `col` chạm 80: tự xuống dòng (wrap), nếu không chữ sẽ tràn sang... đầu hàng sau một cách tình cờ, còn `row` thì sai.

`print(chuỗi)` chỉ là vòng lặp gọi `putc`.

# Việc cần làm

1. Viết `clear()` tô màn hình và đưa con trỏ về (0, 0).
2. Hoàn thiện `putc`: mã khởi đầu chưa xử lý `\\n` và chưa wrap.
3. In đúng như đề: sau `Line 2` phải xuống dòng, rồi 100 chữ `x` chiếm trọn hàng 2 và 20 ô đầu của hàng 3.
""",
    starter="""#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void putc(char ch) {
    // TODO: xử lý '\\n' (về đầu dòng kế tiếp) và tự xuống dòng khi col chạm COLS
    VGA[row * COLS + col] = cell(ch, A);
    col++;
}

static void print(const char *s) { while (*s) putc(*s++); }

extern "C" void kmain() {
    // TODO: xoá màn hình trước khi in (màn hình đang còn chữ của BIOS)
    print("Line 1\\nLine 2\\n");
    for (int i = 0; i < 100; i++) putc('x');
    serial_print("UI OK\\n");
    halt();
}
""",
    tests=[
        BOOTED,
        {"id": "clear", "points": 20, "expect": {"cells": cells((0, 7, {"text": " " * 40}), (1, 7, {"text": " " * 40}), (4, 0, {"text": " " * 40}), (5, 0, {"text": " " * 40}), (6, 0, {"text": " " * 40}))},
         "concept": "kernel thừa hưởng màn hình của BIOS/bootloader; phải tự xoá trước khi vẽ"},
        {"id": "newline", "points": 35, "expect": {"cells": cells((0, 0, {"text": "Line 1 "}), (1, 0, {"text": "Line 2 "}))},
         "concept": "'\\n' không phải ký tự để vẽ mà là lệnh cho con trỏ: cột về 0, hàng tăng 1"},
        {"id": "wrap", "points": 35, "expect": {"cells": cells((2, 0, {"text": "x" * 80}), (3, 0, {"text": "x" * 20 + " "}))},
         "concept": "khi cột chạm 80 phải cập nhật cả hàng lẫn cột, nếu không vị trí con trỏ lệch khỏi thực tế"},
    ])

# ------------------------------------------------------------------ 3
LABS["ui-03-window"] = dict(
    title="3. Vẽ khung cửa sổ",
    statement="Viết `window(r, c, h, w, title, a)` vẽ một cửa sổ có viền bằng ký tự khung CP437 và tiêu đề căn giữa trên viền trên. Vẽ nền desktop 0x1F và một cửa sổ tại (5, 20), cao 10, rộng 40, tiêu đề ` Hello `, thuộc tính 0x70.",
    lesson="""# Cửa sổ chỉ là hình chữ nhật các ô

Bảng mã CP437 của VGA có sẵn các ký tự vẽ khung. `ui.h` đặt tên cho chúng:

```
BOX_TL ┌   BOX_H ─   BOX_TR ┐
BOX_V  │             BOX_V  │
BOX_BL └   BOX_H ─   BOX_BR ┘
```

Một cửa sổ cao `h`, rộng `w` đặt tại (r, c) gồm:

- 4 góc ở (r, c), (r, c+w-1), (r+h-1, c), (r+h-1, c+w-1).
- Viền ngang ở hàng đầu và hàng cuối, viền dọc ở cột đầu và cột cuối.
- Phần ruột: dấu cách mang thuộc tính của cửa sổ — đây là thứ "che" nội dung bên dưới.

Tiêu đề căn giữa: nếu tiêu đề dài `n` thì bắt đầu ở cột `c + (w - n) / 2`.

# Việc cần làm

Hoàn thiện `window`. Mã khởi đầu mới vẽ một góc. Hãy nghĩ theo toạ độ tương đối (x, y) bên trong cửa sổ rồi mới cộng (r, c): cách này dùng lại được cho mọi vị trí.
""",
    starter="""#include "ui.h"

static void put(int r, int c, char ch, u8 a) { VGA[r * COLS + c] = cell(ch, a); }

static void window(int r, int c, int h, int w, const char *title, u8 a) {
    put(r, c, BOX_TL, a);
    // TODO: 3 góc còn lại, viền ngang/dọc, phần ruột (dấu cách), tiêu đề căn giữa trên viền trên
    put(r + h - 1, c + w - 1, title[0], a);  // dòng tạm để dùng hết tham số; hãy thay bằng mã của bạn
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', attr(WHITE, BLUE));
    window(5, 20, 10, 40, " Hello ", attr(BLACK, LIGHT_GREY));
    serial_print("UI OK\\n");
    halt();
}
""",
    tests=[
        BOOTED,
        {"id": "corners", "points": 25, "expect": {"cells": cells((5, 20, {"text": "┌"}), (5, 59, {"text": "┐"}), (14, 20, {"text": "└"}), (14, 59, {"text": "┘"}))},
         "concept": "góc dưới phải nằm ở (r + h - 1, c + w - 1): lỗi lệch một đơn vị là lỗi phổ biến nhất khi vẽ khung"},
        {"id": "borders", "points": 25, "expect": {"cells": cells((5, 21, {"text": "─" * 8}), (14, 21, {"text": "─" * 38}), (9, 20, {"text": "│"}), (9, 59, {"text": "│"}))},
         "concept": "VGA dùng bảng mã CP437: mã 0xC4 và 0xB3 là nét ngang và nét dọc"},
        {"id": "body", "points": 20, "expect": {"cells": cells((6, 21, {"text": " " * 38, "attr": "70"}), (13, 21, {"text": " " * 38, "attr": "70"}), (4, 20, {"len": 40, "attr": "1f"}), (9, 19, {"len": 1, "attr": "1f"}))},
         "concept": "phần ruột phải được tô, vì cửa sổ che nội dung bên dưới bằng chính các ô của nó"},
        {"id": "title", "points": 20, "expect": {"cells": cells((5, 36, {"text": " Hello ", "attr": "70"}), (5, 35, {"text": "─"}), (5, 43, {"text": "─"}))},
         "concept": "căn giữa: cột bắt đầu = c + (w - độ dài tiêu đề) / 2"},
    ])

# ------------------------------------------------------------------ 4
LABS["ui-04-input"] = dict(
    title="4. Bàn phím: nhập một dòng",
    statement="In dấu nhắc `> `, hiển thị các phím người dùng gõ, hỗ trợ Backspace. Khi nhấn Enter, in `You typed: <nội dung>` ở dòng kế tiếp rồi in dấu nhắc mới.",
    script=[{"wait": 2}, {"keys": ["h", "e", "l", "p", "x", "backspace", "ret"]}, {"wait": 1}],
    lesson="""# Bàn phím không gửi chữ, nó gửi sự kiện

Bộ điều khiển PS/2 đặt một byte gọi là scancode ở cổng `0x60` mỗi khi có phím được **nhấn** hoặc **nhả**:

- Nhấn phím `A` -> `0x1E` (make code).
- Nhả phím `A` -> `0x9E` = `0x1E | 0x80` (break code).

Vì thế nếu in mọi scancode nhận được, mỗi phím sẽ sinh hai sự kiện. Bit 7 cho biết đó là nhả phím.

`ui.h` có sẵn:

- `kbd_scancode()`: chờ và trả về một scancode (polling cổng 0x64/0x60).
- `KEYMAP[make_code]`: ký tự ASCII tương ứng, hoặc 0 nếu phím không sinh ký tự (Shift, Ctrl...).
- `KEY_ENTER`, `KEY_BACKSPACE`.

# Soạn một dòng

Giao diện nhập liệu cần hai thứ đi đôi: bộ đệm `line[]` giữ nội dung, và màn hình hiển thị nội dung đó. Backspace phải sửa **cả hai**: bớt một ký tự trong bộ đệm, lùi con trỏ và xoá ô trên màn hình. Đừng cho xoá lấn vào dấu nhắc.

# Việc cần làm

Mã khởi đầu in mọi scancode thành ký tự (kể cả lúc nhả phím). Hãy bỏ qua break code, xử lý Enter và Backspace như đề.

Dùng **Chạy trực tiếp** để gõ thử trên kernel của bạn.
""",
    starter="""#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void putc(char ch) {
    if (ch == '\\n') {
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
""",
    tests=[
        {"id": "echo", "points": 30, "expect": {"cells": cells((0, 0, {"text": "> help"}))},
         "concept": "mỗi phím sinh hai scancode (nhấn và nhả); bit 7 bật nghĩa là nhả phím"},
        {"id": "backspace", "points": 30, "expect": {"cells": cells((0, 0, {"text": "> help  "}))},
         "concept": "Backspace phải sửa cả bộ đệm lẫn màn hình: lùi con trỏ và xoá ô vừa lùi qua"},
        {"id": "enter", "points": 40, "expect": {"cells": cells((1, 0, {"text": "You typed: help "}), (2, 0, {"text": ">  "}))},
         "concept": "bộ đệm dòng là nguồn sự thật; màn hình chỉ là hình ảnh của nó"},
    ])

# ------------------------------------------------------------------ 5
LABS["ui-05-scroll"] = dict(
    title="5. Cuộn màn hình",
    statement="Bổ sung cuộn cho console: khi con trỏ vượt quá hàng cuối, dịch toàn bộ nội dung lên một hàng và xoá hàng cuối. Kernel in `line 0` tới `line 29`, mỗi dòng kết thúc bằng xuống dòng.",
    lesson="""# Khi hết màn hình

Màn hình chỉ có 25 hàng. Console của bài 2 sẽ ghi tiếp vào vùng nhớ **sau** màn hình khi `row` đạt 25 — không báo lỗi, không hiện gì, chỉ âm thầm ghi ra ngoài mảng.

Cuộn (scroll) là thao tác bộ nhớ thuần tuý:

1. Sao chép hàng 1..24 lên hàng 0..23: ô `i` nhận giá trị của ô `i + 80`.
2. Xoá hàng 24.
3. Đặt `row = 24`.

Chú ý chiều sao chép: đi từ chỉ số nhỏ tới lớn. Nguồn và đích chồng lên nhau, sao chép ngược chiều sẽ nhân bản một hàng ra toàn màn hình. Đây chính là lý do thư viện C có cả `memcpy` lẫn `memmove`.

# Việc cần làm

Viết `scroll()` và gọi nó trong `putc` đúng lúc. Sau khi in 30 dòng (dòng cuối cũng kết thúc bằng `\\n`), hàng 0 phải là `line 6`, hàng 23 là `line 29`, hàng 24 trống.
""",
    starter="""#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void putc(char ch) {
    if (ch == '\\n') {
        col = 0;
        row++;
    } else {
        VGA[row * COLS + col] = cell(ch, A);
        if (++col == COLS) {
            col = 0;
            row++;
        }
    }
    // TODO: nếu row vượt quá hàng cuối thì cuộn màn hình lên một hàng
}

static void print(const char *s) { while (*s) putc(*s++); }

static void print_num(int v) {
    char digits[12];
    int n = 0;
    do {
        digits[n++] = static_cast<char>('0' + v % 10);
        v /= 10;
    } while (v > 0);
    while (n > 0) putc(digits[--n]);
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    for (int i = 0; i < 30; i++) {
        print("line ");
        print_num(i);
        putc('\\n');
    }
    serial_print("UI OK\\n");
    halt();
}
""",
    tests=[
        BOOTED,
        {"id": "top", "points": 40, "expect": {"cells": cells((0, 0, {"text": "line 6 "}), (1, 0, {"text": "line 7 "}))},
         "concept": "cuộn = dịch 24 hàng lên trên trong bộ nhớ; vùng nguồn và đích chồng nhau nên chiều sao chép quan trọng"},
        {"id": "bottom", "points": 30, "expect": {"cells": cells((23, 0, {"text": "line 29 "}), (22, 0, {"text": "line 28 "}))},
         "concept": "sau khi cuộn, con trỏ phải nằm ở hàng cuối, không phải ngoài màn hình"},
        {"id": "last-row", "points": 20, "expect": {"row": 24, "vga_re": "^$"},
         "concept": "hàng cuối phải được xoá sau khi dịch, nếu không nội dung cũ bị lặp lại"},
    ])

# ------------------------------------------------------------------ 6
LABS["ui-06-menu"] = dict(
    title="6. Menu và phím mũi tên",
    statement="Vẽ thanh tiêu đề `MENU` (hàng 0) và menu ba mục `Open`, `Save`, `Quit` ở hàng 2-4, cột 4. Mục đang chọn tô đảo màu (0x70), mục khác 0x07. Mũi tên lên/xuống đổi mục (đi vòng), Enter ghi `Selected: <mục>` lên thanh trạng thái (hàng 24).",
    script=[{"wait": 2}, {"snap": "start"}, {"keys": ["down", "down"]}, {"wait": 0.4}, {"snap": "moved"},
            {"keys": ["up", "ret"]}, {"wait": 1}],
    lesson="""# Giao diện = trạng thái + hàm vẽ

Từ bài này, màn hình không còn là thứ bạn "in dần ra". Nó là **hình ảnh của một trạng thái**: ở đây trạng thái chỉ là một số nguyên `selected`. Vòng lặp của mọi giao diện đều giống nhau:

```
vẽ(trạng thái)
lặp:
    chờ sự kiện bàn phím
    cập nhật trạng thái
    vẽ lại(trạng thái)
```

Đừng cố "xoá vệt sáng cũ rồi tô vệt sáng mới" bằng tay ở nhiều chỗ: hãy có một hàm `draw(selected)` vẽ lại cả menu từ trạng thái. Ít mã hơn và không thể lệch.

# Phím mở rộng

Phím mũi tên không có trong bảng scancode gốc nên bàn phím gửi **hai byte**: tiền tố `0xE0` rồi tới mã phím (`KEY_UP` = 0x48, `KEY_DOWN` = 0x50). Khi nhả phím cũng vậy: `0xE0` rồi mã | 0x80.

Bạn cần nhớ "byte trước có phải 0xE0 không" — một máy trạng thái nhỏ. Nếu bỏ qua tiền tố, 0x48 và 0x50 sẽ bị hiểu nhầm thành phím số trên bàn phím số.

# Việc cần làm

Mã khởi đầu đã vẽ menu tĩnh. Hãy xử lý 0xE0, mũi tên (đi vòng: lên từ mục đầu tới mục cuối), và Enter.

Dùng **Chạy trực tiếp** rồi bấm mũi tên để thử.
""",
    starter="""#include "ui.h"

static const u8 NORMAL = attr(LIGHT_GREY, BLACK), INVERSE = attr(BLACK, LIGHT_GREY);
static const char *const ITEMS[3] = {"Open", "Save", "Quit"};

static void text(int r, int c, const char *s, u8 a) {
    for (; *s; s++, c++) VGA[r * COLS + c] = cell(*s, a);
}

static void bar(int r, const char *s) {
    for (int x = 0; x < COLS; x++) VGA[r * COLS + x] = cell(' ', INVERSE);
    text(r, 1, s, INVERSE);
}

static void draw(int selected) {
    for (int i = 0; i < 3; i++) {
        const u8 a = i == selected ? INVERSE : NORMAL;
        for (int x = 2; x < 22; x++) VGA[(2 + i) * COLS + x] = cell(' ', a);
        text(2 + i, 4, ITEMS[i], a);
    }
}

extern "C" void kmain() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', NORMAL);
    bar(0, "MENU");
    bar(24, "Up/Down: move   Enter: select");
    int selected = 0;
    draw(selected);
    for (;;) {
        const u8 sc = kbd_scancode();
        // TODO: nhớ tiền tố 0xE0; KEY_UP / KEY_DOWN đổi selected (đi vòng); KEY_ENTER ghi "Selected: ..." lên hàng 24
        if (sc == KEY_ENTER) bar(24, "Selected: ?");
        draw(selected);
    }
}
""",
    tests=[
        {"id": "layout", "points": 20, "expect": {"at": "start", "cells": cells((0, 1, {"text": "MENU", "attr": "70"}), (0, 79, {"len": 1, "attr": "70"}), (2, 4, {"text": "Open", "attr": "70"}), (3, 4, {"text": "Save", "attr": "07"}), (4, 4, {"text": "Quit", "attr": "07"}))},
         "concept": "thanh tiêu đề và vệt chọn chỉ là các ô có thuộc tính đảo màu (nền sáng, chữ tối)"},
        {"id": "move-down", "points": 30, "expect": {"at": "moved", "cells": cells((4, 4, {"text": "Quit", "attr": "70"}), (2, 4, {"text": "Open", "attr": "07"}), (3, 4, {"text": "Save", "attr": "07"}))},
         "concept": "phím mũi tên gửi tiền tố 0xE0 rồi mới tới mã phím; phải nhớ trạng thái giữa hai byte"},
        {"id": "move-up", "points": 20, "expect": {"cells": cells((3, 4, {"text": "Save", "attr": "70"}), (4, 4, {"text": "Quit", "attr": "07"}))},
         "concept": "vẽ lại toàn bộ menu từ trạng thái thay vì sửa từng ô: vệt chọn cũ tự biến mất"},
        {"id": "select", "points": 30, "expect": {"row": 24, "vga": "Selected: Save", "cells": cells((24, 0, {"len": 80, "attr": "70"}))},
         "concept": "Enter là make code 0x1C không có tiền tố; thanh trạng thái là nơi giao diện phản hồi người dùng"},
    ])

# ------------------------------------------------------------------ 7
LABS["ui-07-shell"] = dict(
    title="7. Shell tí hon",
    statement="Ghép console, cuộn và nhập dòng thành một shell với dấu nhắc `os> `. Lệnh: `help` (in `commands: help echo clear`), `echo <văn bản>`, `clear`. Lệnh lạ in `unknown command: <lệnh>`.",
    script=[{"wait": 2}, {"keys": ["e", "c", "h", "o", "spc", "h", "i", "ret"]}, {"wait": 0.4}, {"snap": "echo"},
            {"keys": ["h", "e", "l", "p", "ret"]}, {"wait": 0.4}, {"snap": "help"},
            {"keys": ["c", "l", "e", "a", "r", "ret", "f", "o", "o", "ret"]}, {"wait": 1}],
    lesson="""# Giao diện dòng lệnh

Shell là giao diện người dùng đầu tiên của hầu hết hệ điều hành. Nó chỉ là một vòng lặp:

```
lặp mãi:
    in dấu nhắc
    đọc một dòng
    phân tích và chạy lệnh
```

Bạn đã có đủ các mảnh: console có cuộn (bài 5), nhập dòng có Backspace (bài 4). Mã khởi đầu đã ghép chúng lại; việc của bạn là phần **diễn giải lệnh**.

# So sánh chuỗi không có thư viện

Không có `strcmp` hay `std::string`. Hai hàm nhỏ là đủ:

- `equal(a, b)`: đi song song trên hai chuỗi tới khi khác nhau hoặc gặp ký tự kết thúc.
- `starts_with(s, tiền_tố)`: để nhận ra `echo ` và lấy phần còn lại làm tham số (`line + 5`).

# Việc cần làm

Hoàn thiện `run(line)`:

- Dòng rỗng: không làm gì.
- `help`, `echo <văn bản>`, `clear`, và thông báo cho lệnh lạ, đúng nguyên văn như đề.
- Sau `clear`, dấu nhắc kế tiếp phải ở hàng 0.

Dùng **Chạy trực tiếp** để gõ lệnh vào shell của bạn.
""",
    starter="""#include "ui.h"

static int row, col;
static const u8 A = attr(LIGHT_GREY, BLACK);

static void clear() {
    for (int i = 0; i < COLS * ROWS; i++) VGA[i] = cell(' ', A);
    row = col = 0;
}

static void scroll() {
    for (int i = 0; i < (ROWS - 1) * COLS; i++) VGA[i] = VGA[i + COLS];
    for (int i = (ROWS - 1) * COLS; i < ROWS * COLS; i++) VGA[i] = cell(' ', A);
    row = ROWS - 1;
}

static void putc(char ch) {
    if (ch == '\\n') {
        col = 0;
        row++;
    } else {
        VGA[row * COLS + col] = cell(ch, A);
        if (++col == COLS) {
            col = 0;
            row++;
        }
    }
    if (row == ROWS) scroll();
}

static void print(const char *s) { while (*s) putc(*s++); }

static void read_line(char *line, int cap) {
    int n = 0;
    for (;;) {
        const u8 sc = kbd_scancode();
        if (sc & 0x80) continue;
        if (sc == KEY_ENTER) break;
        if (sc == KEY_BACKSPACE) {
            if (n > 0 && col > 0) {
                n--;
                col--;
                VGA[row * COLS + col] = cell(' ', A);
            }
        } else if (const char ch = KEYMAP[sc]; ch >= ' ' && n < cap - 1) {
            line[n++] = ch;
            putc(ch);
        }
    }
    line[n] = 0;
    putc('\\n');
}

static void run(const char *line) {
    // TODO: dòng rỗng; "help"; "echo <văn bản>"; "clear"; lệnh lạ
    print("unknown command: ");
    print(line);
    putc('\\n');
}

extern "C" void kmain() {
    clear();
    char line[64];
    for (;;) {
        print("os> ");
        read_line(line, 64);
        run(line);
    }
}
""",
    tests=[
        {"id": "echo", "points": 30, "expect": {"at": "echo", "cells": cells((0, 0, {"text": "os> echo hi "}), (1, 0, {"text": "hi "}), (2, 0, {"text": "os>  "}))},
         "concept": "tách lệnh và tham số: nhận ra tiền tố `echo ` rồi dùng phần còn lại của dòng"},
        {"id": "help", "points": 20, "expect": {"at": "help", "cells": cells((3, 0, {"text": "commands: help echo clear "}), (4, 0, {"text": "os>  "}))},
         "concept": "so sánh chuỗi trong kernel phải tự viết: đi song song hai chuỗi tới ký tự kết thúc"},
        {"id": "clear", "points": 25, "expect": {"cells": cells((0, 0, {"text": "os> foo "}), (3, 0, {"len": 80, "text": " " * 80}))},
         "concept": "clear phải đặt lại cả con trỏ, nếu không dấu nhắc kế tiếp hiện ở giữa màn hình trống"},
        {"id": "unknown", "points": 25, "expect": {"cells": cells((1, 0, {"text": "unknown command: foo "}), (2, 0, {"text": "os>  "}))},
         "concept": "giao diện tốt luôn phản hồi: lệnh lạ phải được báo lại thay vì im lặng"},
    ])

# ------------------------------------------------------------------ 8
LABS["ui-08-windows"] = dict(
    title="8. Nhiều cửa sổ, focus và thứ tự chồng",
    statement="Quản lý hai cửa sổ chồng nhau: A tại (2, 5) và B tại (6, 20), mỗi cái cao 10, rộng 30. Cửa sổ có focus được vẽ sau cùng (nằm trên) và có thanh tiêu đề 0x1F; cửa sổ kia 0x70. Tab đổi focus; ký tự gõ vào được thêm vào dòng đầu của cửa sổ đang focus.",
    script=[{"wait": 2}, {"snap": "start"}, {"keys": ["x", "tab", "y"]}, {"wait": 0.4}, {"snap": "second"},
            {"keys": ["tab", "z"]}, {"wait": 1}],
    lesson="""# Trình quản lý cửa sổ thu nhỏ

Đây là ý tưởng lõi của mọi giao diện cửa sổ, kể cả đồ hoạ: **mỗi cửa sổ sở hữu nội dung của riêng nó**, còn màn hình được dựng lại từ danh sách cửa sổ.

Vì sao không vẽ thẳng lên màn hình như trước? Vì khi B đè lên A rồi lại bị đưa xuống dưới, phần của A từng bị che phải hiện lại — mà màn hình không nhớ nó. Nội dung phải nằm trong cấu trúc dữ liệu của cửa sổ (`text`, `n`), không phải trong bộ nhớ VGA.

# Thuật toán hoạ sĩ

Vẽ từ sau ra trước: desktop, rồi cửa sổ không có focus, cuối cùng là cửa sổ có focus. Cái vẽ sau tự che cái vẽ trước; bạn không cần tính phần giao nhau.

# Focus

Focus quyết định hai việc: phím gõ đi vào cửa sổ nào, và cửa sổ nào nằm trên. Người dùng cần **nhìn thấy** focus: ở đây là màu thanh tiêu đề (hàng viền trên): 0x1F khi có focus, 0x70 khi không.

# Quy ước của bài

- Tiêu đề (` A `, ` B `) in từ cột `c + 2` trên hàng viền trên.
- Nội dung của cửa sổ in từ ô (r + 1, c + 1).
- Lúc đầu A có focus.

# Việc cần làm

Mã khởi đầu vẽ hai cửa sổ một lần và chưa phản ứng với bàn phím. Hãy viết `repaint(focus)` và vòng lặp sự kiện: Tab đổi focus, ký tự in được thêm vào `text` của cửa sổ đang focus, rồi vẽ lại.

Câu hỏi để nghĩ thêm: vẽ lại toàn bộ màn hình sau mỗi phím có lãng phí không? Các hệ thống thật chỉ vẽ lại vùng "bẩn" — nhưng chỉ sau khi phiên bản đơn giản đã đúng.
""",
    starter="""#include "ui.h"

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
""",
    tests=[
        {"id": "initial", "points": 20, "expect": {"at": "start", "cells": cells((2, 5, {"text": "┌", "attr": "1f"}), (2, 7, {"text": " A ", "attr": "1f"}), (6, 20, {"text": " ", "attr": "70"}), (6, 40, {"text": "─", "attr": "70"}), (15, 49, {"text": "┘"}))},
         "concept": "thuật toán hoạ sĩ: vẽ từ sau ra trước, cửa sổ có focus vẽ sau cùng nên nằm trên"},
        {"id": "focus-switch", "points": 30, "expect": {"at": "second", "cells": cells((6, 20, {"text": "┌", "attr": "1f"}), (6, 22, {"text": " B ", "attr": "1f"}), (2, 5, {"text": "┌", "attr": "70"}), (2, 7, {"text": " A ", "attr": "70"}))},
         "concept": "focus phải nhìn thấy được: thanh tiêu đề đổi màu và cửa sổ nổi lên trên"},
        {"id": "input-routing", "points": 25, "expect": {"at": "second", "cells": cells((3, 6, {"text": "x "}), (7, 21, {"text": "y "}))},
         "concept": "sự kiện bàn phím được chuyển tới cửa sổ đang có focus, không phải tới màn hình"},
        {"id": "restore", "points": 25, "expect": {"cells": cells((3, 6, {"text": "xz "}), (7, 21, {"text": " ", "attr": "70"}), (2, 5, {"text": "┌", "attr": "1f"}), (6, 40, {"text": "─", "attr": "70"}))},
         "concept": "nội dung thuộc về cửa sổ chứ không thuộc về màn hình: nhờ vậy phần từng bị che mới vẽ lại được"},
    ])

for level, (lab_id, lab) in enumerate(LABS.items(), 1):
    d = repo / "labs" / lab_id
    for sub in ("starter", "scaffold"):
        (d / sub).mkdir(parents=True, exist_ok=True)
    spec = {"mode": "toy", "template": "toy-kernel", "track": TRACK, "level": level, "title": lab["title"],
            "statement": lab["statement"], "files": {"required": ["kernel.cpp"], "only": ["kernel.cpp"], "max_bytes": 32768},
            "weights": W, "penalties": {"reset": 30, "bad_image": 100}}
    if "script" in lab:
        spec["script"] = lab["script"]
    spec["tests"] = lab["tests"]
    (d / "lab.json").write_text(json.dumps(spec, ensure_ascii=False, indent=1) + "\n")
    (d / "lesson.md").write_text(lab["lesson"])
    (d / "starter/kernel.cpp").write_text(lab["starter"])
    (d / "scaffold/boot.S").write_text(BOOT)
    shutil.copyfile(ui_h, d / "scaffold/ui.h")
print(len(LABS), "labs written")

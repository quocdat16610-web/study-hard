# Bàn phím không gửi chữ, nó gửi sự kiện

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

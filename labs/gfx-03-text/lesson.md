# Chữ cũng chỉ là điểm ảnh

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

Sau mỗi ký tự, dịch sang phải `FONT_ADVANCE` = 6 điểm (5 cột chữ + 1 cột trống). Gặp `\n`: quay về x ban đầu và tăng y thêm `FONT_H + 2`.

# Việc cần làm

Mã khởi đầu vẽ mỗi ký tự thành một khối đặc. Hãy hoàn thiện `draw_char` để dùng dữ liệu font, và thêm xử lý `\n` vào `draw_text`.

Tại sao font có sẵn chỉ gồm chữ hoa? Vì vẽ font là việc thủ công: mỗi ký tự là 7 con số. Thử sửa một ký tự của riêng bạn bằng cách vẽ nó bằng các lệnh `put_pixel`.

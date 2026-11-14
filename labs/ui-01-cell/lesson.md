# Màn hình là một mảng

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
3. Gọi `serial_print("UI OK\n")`.

Bấm **Chạy thử** sau mỗi thay đổi để thấy màn hình đổi theo.

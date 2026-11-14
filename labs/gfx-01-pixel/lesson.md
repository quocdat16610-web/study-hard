# Từ ô ký tự sang điểm ảnh

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
4. `serial_print("GFX OK\n")`.

Đường chéo thì sao? Thử vẽ thêm sau khi xong bài: nó là lý do các thuật toán vẽ đường thẳng ra đời.

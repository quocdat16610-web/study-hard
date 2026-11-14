# Chuột nói gì với kernel

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

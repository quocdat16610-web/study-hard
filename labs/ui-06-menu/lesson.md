# Giao diện = trạng thái + hàm vẽ

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

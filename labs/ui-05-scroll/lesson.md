# Khi hết màn hình

Màn hình chỉ có 25 hàng. Console của bài 2 sẽ ghi tiếp vào vùng nhớ **sau** màn hình khi `row` đạt 25 — không báo lỗi, không hiện gì, chỉ âm thầm ghi ra ngoài mảng.

Cuộn (scroll) là thao tác bộ nhớ thuần tuý:

1. Sao chép hàng 1..24 lên hàng 0..23: ô `i` nhận giá trị của ô `i + 80`.
2. Xoá hàng 24.
3. Đặt `row = 24`.

Chú ý chiều sao chép: đi từ chỉ số nhỏ tới lớn. Nguồn và đích chồng lên nhau, sao chép ngược chiều sẽ nhân bản một hàng ra toàn màn hình. Đây chính là lý do thư viện C có cả `memcpy` lẫn `memmove`.

# Việc cần làm

Viết `scroll()` và gọi nó trong `putc` đúng lúc. Sau khi in 30 dòng (dòng cuối cũng kết thúc bằng `\n`), hàng 0 phải là `line 6`, hàng 23 là `line 29`, hàng 24 trống.

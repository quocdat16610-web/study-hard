# Ghép các viên gạch

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

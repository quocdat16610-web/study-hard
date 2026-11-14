# Hình chữ nhật: viên gạch của mọi giao diện

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

# Kéo thả là một máy trạng thái

Click (bài 6) là một khoảnh khắc. Kéo thả thì kéo dài qua nhiều gói tin chuột, nên kernel phải **nhớ** mình đang ở giữa một thao tác:

```
          nhấn trên thanh tiêu đề
  RẢNH  ------------------------->  ĐANG KÉO cửa sổ k
        <-------------------------
                nhả nút
```

- Ở trạng thái RẢNH, chuột di chuyển chỉ làm con trỏ đi.
- Ở trạng thái ĐANG KÉO, mỗi lần chuột di chuyển thì cửa sổ k đi theo.

Trạng thái này chỉ cần một biến: chỉ số cửa sổ đang kéo, hoặc -1 khi rảnh.

# Giữ nguyên điểm đã nắm

Nếu gán thẳng `win.x = cx`, góc trên trái của cửa sổ sẽ nhảy tới con trỏ ngay khi bắt đầu kéo. Người dùng nắm cửa sổ ở đâu thì điểm đó phải ở dưới con trỏ suốt quá trình.

Lúc nhấn nút, ghi lại **độ lệch** giữa con trỏ và gốc cửa sổ:

```
grab_x = cx - win.x        grab_y = cy - win.y
```

Trong khi kéo, đặt lại gốc cửa sổ sao cho độ lệch đó không đổi:

```
win.x = cx - grab_x        win.y = cy - grab_y
```

# Kéo từ đâu

Chỉ thanh tiêu đề mới là "tay nắm": hàng viền trên cùng và 12 hàng tiêu đề, tức `cy < win.y + 13`. Nhấn trong thân cửa sổ vẫn đưa nó lên trên (như bài 6) nhưng không bắt đầu kéo — phần thân dành cho nội dung của ứng dụng.

Thứ tự hit testing vẫn như bài 6: cửa sổ trên trước, cửa sổ dưới sau.

# Vì sao bài 2 quan trọng

Cửa sổ giờ có thể bị kéo ra ngoài mép màn hình, toạ độ có thể âm. Mọi thứ vẫn đúng vì `fill_rect` đã cắt xén từ bài 2, và mỗi khung hình được dựng lại từ đầu trong back buffer nên không để lại vệt.

# Việc cần làm

Mã khởi đầu là desktop hoàn chỉnh của bài 6. Hãy thêm:

1. Biến trạng thái kéo và độ lệch điểm nắm.
2. Ở cạnh lên của nút trái: tìm cửa sổ bị nhấn, đưa nó lên trên, và nếu nhấn trên thanh tiêu đề thì bắt đầu kéo.
3. Khi nút nhả: kết thúc kéo.
4. Khi đang kéo: cập nhật vị trí cửa sổ trước khi `compose()`.

Dùng **Chạy trực tiếp**: nhấn giữ trên thanh tiêu đề rồi rê chuột.

Câu hỏi để nghĩ thêm: nếu kéo cửa sổ ra hẳn ngoài màn hình thì làm sao lấy lại? Các hệ điều hành thật luôn giữ một phần thanh tiêu đề trong màn hình.

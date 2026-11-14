# Trình quản lý cửa sổ thu nhỏ

Đây là ý tưởng lõi của mọi giao diện cửa sổ, kể cả đồ hoạ: **mỗi cửa sổ sở hữu nội dung của riêng nó**, còn màn hình được dựng lại từ danh sách cửa sổ.

Vì sao không vẽ thẳng lên màn hình như trước? Vì khi B đè lên A rồi lại bị đưa xuống dưới, phần của A từng bị che phải hiện lại — mà màn hình không nhớ nó. Nội dung phải nằm trong cấu trúc dữ liệu của cửa sổ (`text`, `n`), không phải trong bộ nhớ VGA.

# Thuật toán hoạ sĩ

Vẽ từ sau ra trước: desktop, rồi cửa sổ không có focus, cuối cùng là cửa sổ có focus. Cái vẽ sau tự che cái vẽ trước; bạn không cần tính phần giao nhau.

# Focus

Focus quyết định hai việc: phím gõ đi vào cửa sổ nào, và cửa sổ nào nằm trên. Người dùng cần **nhìn thấy** focus: ở đây là màu thanh tiêu đề (hàng viền trên): 0x1F khi có focus, 0x70 khi không.

# Quy ước của bài

- Tiêu đề (` A `, ` B `) in từ cột `c + 2` trên hàng viền trên.
- Nội dung của cửa sổ in từ ô (r + 1, c + 1).
- Lúc đầu A có focus.

# Việc cần làm

Mã khởi đầu vẽ hai cửa sổ một lần và chưa phản ứng với bàn phím. Hãy viết `repaint(focus)` và vòng lặp sự kiện: Tab đổi focus, ký tự in được thêm vào `text` của cửa sổ đang focus, rồi vẽ lại.

Câu hỏi để nghĩ thêm: vẽ lại toàn bộ màn hình sau mỗi phím có lãng phí không? Các hệ thống thật chỉ vẽ lại vùng "bẩn" — nhưng chỉ sau khi phiên bản đơn giản đã đúng.

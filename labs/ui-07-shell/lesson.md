# Giao diện dòng lệnh

Shell là giao diện người dùng đầu tiên của hầu hết hệ điều hành. Nó chỉ là một vòng lặp:

```
lặp mãi:
    in dấu nhắc
    đọc một dòng
    phân tích và chạy lệnh
```

Bạn đã có đủ các mảnh: console có cuộn (bài 5), nhập dòng có Backspace (bài 4). Mã khởi đầu đã ghép chúng lại; việc của bạn là phần **diễn giải lệnh**.

# So sánh chuỗi không có thư viện

Không có `strcmp` hay `std::string`. Hai hàm nhỏ là đủ:

- `equal(a, b)`: đi song song trên hai chuỗi tới khi khác nhau hoặc gặp ký tự kết thúc.
- `starts_with(s, tiền_tố)`: để nhận ra `echo ` và lấy phần còn lại làm tham số (`line + 5`).

# Việc cần làm

Hoàn thiện `run(line)`:

- Dòng rỗng: không làm gì.
- `help`, `echo <văn bản>`, `clear`, và thông báo cho lệnh lạ, đúng nguyên văn như đề.
- Sau `clear`, dấu nhắc kế tiếp phải ở hàng 0.

Dùng **Chạy trực tiếp** để gõ lệnh vào shell của bạn.

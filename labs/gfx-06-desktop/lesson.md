# Vì sao cần back buffer

Ở bài 5, con trỏ phải tự lưu và trả lại nền. Với hai cửa sổ chồng nhau, cách đó không còn đủ: khi B nổi lên trên, phần của A bị che phải biến mất; khi A nổi lại, nó phải hiện ra nguyên vẹn. Cách đơn giản và đúng nhất là **vẽ lại cả khung hình** mỗi khi có thay đổi.

Nhưng nếu vẽ lại thẳng lên màn hình, người dùng sẽ thấy cảnh dang dở: nền vừa xoá, cửa sổ chưa kịp vẽ — màn hình nhấp nháy. Lời giải là **double buffering**:

```
back[W * H]      vùng nhớ thường, cùng kích thước màn hình
compose():
    vẽ nền, cửa sổ dưới, cửa sổ trên, con trỏ   -> tất cả vào back[]
    chép back[] sang fb[]                        -> một lần duy nhất
```

Màn hình chỉ bao giờ thấy khung hình đã hoàn chỉnh. Con trỏ không cần lưu/khôi phục nền nữa: nó chỉ là lớp vẽ sau cùng của mỗi khung.

# Thứ tự chồng (z-order)

Với hai cửa sổ, z-order chỉ là một số: `top` = chỉ số cửa sổ nằm trên. Vẽ `wins[1 - top]` trước, `wins[top]` sau (thuật toán hoạ sĩ, như bài 8 phần text mode).

# Click vào đâu? (hit testing)

Khi nút trái **vừa được nhấn** (gói này có bit nút trái, gói trước thì không), cần tìm cửa sổ dưới con trỏ. Quy tắc: hỏi theo thứ tự **từ trên xuống**.

- Điểm nằm trong cửa sổ trên: cửa sổ trên nhận, không đổi gì.
- Nếu không, và nằm trong cửa sổ dưới: đưa nó lên trên.

Hỏi sai thứ tự thì click vào vùng chồng nhau sẽ "xuyên" qua cửa sổ trên — một lỗi giao diện rất khó chịu.

Chỉ phản ứng ở **cạnh lên** của nút (từ nhả sang nhấn). Nếu phản ứng mỗi gói tin có nút đang giữ, một lần click sẽ bị xử lý nhiều lần.

# Việc cần làm

Mã khởi đầu vẽ thẳng lên màn hình một lần (sai thứ tự chồng) và để con trỏ lại vệt khi di chuyển. `mouse_read` đã gom gói tin cho bạn. Hãy:

1. Chuyển các hàm vẽ sang ghi vào `back[]`, viết `compose()`.
2. Vẽ đúng z-order theo `top`, con trỏ sau cùng.
3. Xử lý click theo quy tắc hit testing ở trên.

Dùng **Chạy trực tiếp**: rê chuột và click vào các cửa sổ trên màn hình kernel.

# Từ ô nhớ tới "in ra màn hình"

`printf` không tồn tại trong kernel. Thứ gần nhất bạn có là một hàm `putc` tự viết, nhớ vị trí sẽ ghi tiếp theo — gọi là con trỏ (cursor).

Con trỏ chỉ là hai số nguyên `row`, `col`. Mỗi lần in một ký tự:

- Ký tự thường: ghi vào ô (row, col) rồi tăng `col`.
- `\n`: không ghi gì, đưa `col` về 0 và tăng `row`.
- Khi `col` chạm 80: tự xuống dòng (wrap), nếu không chữ sẽ tràn sang... đầu hàng sau một cách tình cờ, còn `row` thì sai.

`print(chuỗi)` chỉ là vòng lặp gọi `putc`.

# Việc cần làm

1. Viết `clear()` tô màn hình và đưa con trỏ về (0, 0).
2. Hoàn thiện `putc`: mã khởi đầu chưa xử lý `\n` và chưa wrap.
3. In đúng như đề: sau `Line 2` phải xuống dòng, rồi 100 chữ `x` chiếm trọn hàng 2 và 20 ô đầu của hàng 3.

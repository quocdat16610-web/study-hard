# Cửa sổ chỉ là hình chữ nhật các ô

Bảng mã CP437 của VGA có sẵn các ký tự vẽ khung. `ui.h` đặt tên cho chúng:

```
BOX_TL ┌   BOX_H ─   BOX_TR ┐
BOX_V  │             BOX_V  │
BOX_BL └   BOX_H ─   BOX_BR ┘
```

Một cửa sổ cao `h`, rộng `w` đặt tại (r, c) gồm:

- 4 góc ở (r, c), (r, c+w-1), (r+h-1, c), (r+h-1, c+w-1).
- Viền ngang ở hàng đầu và hàng cuối, viền dọc ở cột đầu và cột cuối.
- Phần ruột: dấu cách mang thuộc tính của cửa sổ — đây là thứ "che" nội dung bên dưới.

Tiêu đề căn giữa: nếu tiêu đề dài `n` thì bắt đầu ở cột `c + (w - n) / 2`.

# Việc cần làm

Hoàn thiện `window`. Mã khởi đầu mới vẽ một góc. Hãy nghĩ theo toạ độ tương đối (x, y) bên trong cửa sổ rồi mới cộng (r, c): cách này dùng lại được cho mọi vị trí.

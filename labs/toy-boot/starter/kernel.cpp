using u8 = unsigned char;
using u16 = unsigned short;

[[maybe_unused]] static inline void outb(u16 port, u8 v) { asm volatile("outb %0, %1" : : "a"(v), "Nd"(port)); }
static inline u8 inb(u16 port) { u8 v; asm volatile("inb %1, %0" : "=a"(v) : "Nd"(port)); return v; }

// Màn hình text: 80x25 ô, mỗi ô 2 byte (ký tự + thuộc tính màu), ánh xạ tại 0xB8000.
static volatile u16 *const vga = reinterpret_cast<volatile u16 *>(0xB8000);

extern "C" void kmain() {
    // Thử đổi ký tự hoặc màu (byte cao) rồi bấm "Chạy" để thấy màn hình thay đổi.
    vga[0] = 0x1F00 | 'O';
    vga[1] = 0x2F00 | 'S';
    // TODO: gửi "BOOT OK" ra COM1 (cổng 0x3F8), in "Hello, kernel" ở dòng đầu,
    //       rồi đọc bàn phím PS/2 (cổng 0x64/0x60) và hiển thị phím ở dòng thứ hai.
    for (;;) {
        (void)inb(0x64);
    }
}

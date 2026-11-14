// Thư viện tối thiểu cho các bài "Đồ hoạ điểm ảnh" (chỉ đọc, được biên dịch cùng bài của bạn).
#pragma once

using u8 = unsigned char;
using u16 = unsigned short;
using u32 = unsigned int;

constexpr int W = 320;  // chiều rộng màn hình (điểm ảnh)
constexpr int H = 200;  // chiều cao màn hình

static inline void outb(u16 port, u8 v) { asm volatile("outb %0, %1" : : "a"(v), "Nd"(port)); }
static inline void outw(u16 port, u16 v) { asm volatile("outw %0, %1" : : "a"(v), "Nd"(port)); }
static inline void outl(u16 port, u32 v) { asm volatile("outl %0, %1" : : "a"(v), "Nd"(port)); }
static inline u8 inb(u16 port) { u8 v; asm volatile("inb %1, %0" : "=a"(v) : "Nd"(port)); return v; }
static inline u32 inl(u16 port) { u32 v; asm volatile("inl %1, %0" : "=a"(v) : "Nd"(port)); return v; }

// Cổng serial COM1: in thông tin gỡ lỗi (hiện ở khung "Cổng serial").
static inline void serial_print(const char *s) { while (*s) outb(0x3F8, static_cast<u8>(*s++)); }

// Một điểm ảnh là số 32 bit dạng 0x00RRGGBB.
constexpr u32 rgb(u8 r, u8 g, u8 b) { return static_cast<u32>(r) << 16 | static_cast<u32>(g) << 8 | b; }

// ---- Bật chế độ đồ hoạ ---------------------------------------------------------------------
// Card VGA của máy ảo có giao diện "Bochs VBE": ghi (chỉ số, giá trị) qua hai cổng 0x1CE / 0x1CF.
static inline void bga_write(u16 index, u16 value) { outw(0x1CE, index); outw(0x1CF, value); }

// Đọc một thanh ghi 32 bit trong vùng cấu hình PCI của thiết bị (bus, dev, fn).
static inline u32 pci_read(u32 bus, u32 dev, u32 fn, u32 offset) {
    outl(0xCF8, 0x80000000u | bus << 16 | dev << 11 | fn << 8 | (offset & 0xFCu));
    return inl(0xCFC);
}

// Bật chế độ W x H, 32 bit mỗi điểm ảnh, rồi trả về địa chỉ framebuffer (nullptr nếu không thấy card).
// Framebuffer là vùng nhớ của card màn hình: điểm ảnh (x, y) nằm ở fb[y * W + x].
static inline volatile u32 *fb_init() {
    bga_write(4, 0);                      // tắt để đổi cấu hình
    bga_write(1, W);                      // chiều rộng
    bga_write(2, H);                      // chiều cao
    bga_write(3, 32);                     // số bit mỗi điểm ảnh
    bga_write(4, 0x41);                   // bật + dùng framebuffer tuyến tính
    for (u32 dev = 0; dev < 32; dev++) {  // tìm card (vendor 0x1234, device 0x1111); BAR0 là framebuffer
        if (pci_read(0, dev, 0, 0) == 0x11111234u) {
            return reinterpret_cast<volatile u32 *>(pci_read(0, dev, 0, 0x10) & ~0xFu);
        }
    }
    return nullptr;
}

// ---- Chuột PS/2 ----------------------------------------------------------------------------
// Chuột dùng chung bộ điều khiển với bàn phím: cổng dữ liệu 0x60, cổng trạng thái/lệnh 0x64.
static inline void ps2_wait_write() { while (inb(0x64) & 2) {} }
static inline u8 ps2_wait_read() { while (!(inb(0x64) & 1)) {} return inb(0x60); }

// Gửi một lệnh tới chuột (tiền tố 0xD4 báo "byte kế tiếp dành cho chuột") và nhận byte xác nhận 0xFA.
static inline void mouse_command(u8 command) {
    ps2_wait_write();
    outb(0x64, 0xD4);
    ps2_wait_write();
    outb(0x60, command);
    (void)ps2_wait_read();
}

// Bật cổng chuột, đặt cấu hình mặc định (0xF6) và cho phép chuột gửi dữ liệu (0xF4).
static inline void mouse_init() {
    ps2_wait_write();
    outb(0x64, 0xA8);
    mouse_command(0xF6);
    mouse_command(0xF4);
}

// Nếu có một byte từ CHUỘT thì ghi vào `byte` và trả về true. Byte của bàn phím bị bỏ qua.
static inline bool mouse_poll(u8 &byte) {
    const u8 status = inb(0x64);
    if (!(status & 1)) return false;
    byte = inb(0x60);
    return status & 0x20;  // bit 5 của trạng thái: dữ liệu đến từ chuột
}

// Dừng CPU khi kernel không còn gì để làm.
[[noreturn]] static inline void halt() { for (;;) asm volatile("hlt"); }

// Thư viện tối thiểu cho các bài "Giao diện OS" (chỉ đọc, được biên dịch cùng bài của bạn).
#pragma once

using u8 = unsigned char;
using u16 = unsigned short;
using u32 = unsigned int;

constexpr int COLS = 80;
constexpr int ROWS = 25;

// Màn hình text mode: ROWS x COLS ô, ánh xạ tại 0xB8000, ô (hàng, cột) nằm ở VGA[hàng * COLS + cột].
// Mỗi ô 16 bit: byte thấp là ký tự (bảng mã CP437), byte cao là thuộc tính = (màu nền << 4) | màu chữ.
inline volatile u16 *const VGA = reinterpret_cast<volatile u16 *>(0xB8000);

enum Color : u8 {
    BLACK, BLUE, GREEN, CYAN, RED, MAGENTA, BROWN, LIGHT_GREY,
    DARK_GREY, LIGHT_BLUE, LIGHT_GREEN, LIGHT_CYAN, LIGHT_RED, PINK, YELLOW, WHITE
};
constexpr u8 attr(Color fg, Color bg) { return static_cast<u8>(bg << 4 | fg); }
constexpr u16 cell(char ch, u8 a) { return static_cast<u16>(a << 8 | static_cast<u8>(ch)); }

// Ký tự vẽ khung của CP437.
constexpr char BOX_TL = '\xDA', BOX_TR = '\xBF', BOX_BL = '\xC0', BOX_BR = '\xD9', BOX_H = '\xC4', BOX_V = '\xB3';

static inline void outb(u16 port, u8 v) { asm volatile("outb %0, %1" : : "a"(v), "Nd"(port)); }
static inline u8 inb(u16 port) { u8 v; asm volatile("inb %1, %0" : "=a"(v) : "Nd"(port)); return v; }

// Cổng serial COM1: dùng để in thông tin gỡ lỗi (hiện ở khung "Cổng serial").
static inline void serial_print(const char *s) { while (*s) outb(0x3F8, static_cast<u8>(*s++)); }

// Bàn phím PS/2 (polling): chờ tới khi có dữ liệu rồi trả về một scancode (set 1).
// Nhấn phím -> "make code"; nhả phím -> make code | 0x80; phím mở rộng (mũi tên...) có tiền tố 0xE0.
static inline u8 kbd_scancode() { while (!(inb(0x64) & 1)) {} return inb(0x60); }

// Make code -> ASCII cho bàn phím US (0 = phím không sinh ký tự).
inline constexpr char KEYMAP[128] = {
    0, 27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b', '\t',
    'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n', 0, 'a', 's',
    'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`', 0, '\\', 'z', 'x', 'c', 'v',
    'b', 'n', 'm', ',', '.', '/', 0, '*', 0, ' '};
constexpr u8 KEY_UP = 0x48, KEY_DOWN = 0x50, KEY_ENTER = 0x1C, KEY_BACKSPACE = 0x0E, KEY_TAB = 0x0F;

// Dừng CPU khi kernel không còn gì để làm.
[[noreturn]] static inline void halt() { for (;;) asm volatile("hlt"); }

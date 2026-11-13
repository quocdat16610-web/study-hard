using u8 = unsigned char;
using u16 = unsigned short;

static inline void outb(u16 port, u8 v) { asm volatile("outb %0, %1" : : "a"(v), "Nd"(port)); }
static inline u8 inb(u16 port) { u8 v; asm volatile("inb %1, %0" : "=a"(v) : "Nd"(port)); return v; }

static volatile u16 *const vga = reinterpret_cast<volatile u16 *>(0xB8000);
static int cursor = 0;

static void put(char c) { vga[cursor++] = static_cast<u16>(0x0700 | static_cast<u8>(c)); }
static void print(const char *s) { while (*s) put(*s++); }
static void serial(const char *s) { while (*s) outb(0x3F8, static_cast<u8>(*s++)); }

static const char keymap[128] = {
    0, 27, '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', '\b', '\t',
    'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\n', 0, 'a', 's',
    'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', '\'', '`', 0, '\\', 'z', 'x', 'c', 'v',
    'b', 'n', 'm', ',', '.', '/', 0, '*', 0, ' '};

extern "C" void kmain() {
    for (int i = 0; i < 80 * 25; i++) vga[i] = 0x0720;
    print("Hello, kernel");
    cursor = 80;
    serial("BOOT OK\n");
    for (;;) {
        if (!(inb(0x64) & 1)) continue;
        u8 sc = inb(0x60);
        if (sc & 0x80) continue;
        if (char c = keymap[sc]; c >= ' ') put(c);
    }
}

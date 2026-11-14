#include "kapi.h"

void *operator new(unsigned long n) { return kalloc(n); }
void operator delete(void *p) noexcept { kfree_(p); }
void operator delete(void *p, unsigned long) noexcept { kfree_(p); }

class Greeter {
    const char *hello_, *bye_;
public:
    Greeter(const char *h, const char *b) : hello_(h), bye_(b) { kprint(hello_); }
    ~Greeter() { kprint(bye_); }
};

static Greeter *g;

extern "C" int student_init() {
    g = new Greeter("student: init", "student: exit");
    return g ? 0 : -12;
}

extern "C" void student_exit() { delete g; }

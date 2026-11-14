#include "kapi.h"

// Không có thư viện chuẩn: mọi thứ module cần phải đi qua kapi.h.
// TODO: nếu dùng new/delete, hãy tự định nghĩa chúng trên kalloc/kfree_.

extern "C" int student_init() {
    // TODO: in "student: init"
    return 0;
}

extern "C" void student_exit() {
    // TODO: in "student: exit"
}

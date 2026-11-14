/* C ABI between the C glue (which may include Linux headers) and freestanding C++ student code. */
#ifndef KAPI_H
#define KAPI_H
#ifdef __cplusplus
extern "C" {
#endif
void kprint(const char *msg);
void *kalloc(unsigned long size);
void kfree_(void *ptr);
int student_init(void);
void student_exit(void);
#ifdef __cplusplus
}
#endif
#endif

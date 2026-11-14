#include <linux/module.h>
#include <linux/slab.h>
#include "kapi.h"

void kprint(const char *msg) { pr_info("%s\n", msg); }
void *kalloc(unsigned long size) { return kmalloc(size, GFP_KERNEL); }
void kfree_(void *ptr) { kfree(ptr); }

static int __init glue_init(void) { return student_init(); }
static void __exit glue_exit(void) { student_exit(); }

module_init(glue_init);
module_exit(glue_exit);
MODULE_LICENSE("GPL");

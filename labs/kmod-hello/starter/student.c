#include <linux/init.h>
#include <linux/module.h>

static int __init student_init(void)
{
	/* TODO: ghi "student: init" vào kernel log */
	return 0;
}

static void __exit student_exit(void)
{
	/* TODO: ghi "student: exit" vào kernel log */
}

module_init(student_init);
module_exit(student_exit);
/* TODO: khai báo giấy phép của module */

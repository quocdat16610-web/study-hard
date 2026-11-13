#include <linux/init.h>
#include <linux/module.h>

static int __init student_init(void)
{
	pr_info("student: init\n");
	return 0;
}

static void __exit student_exit(void)
{
	pr_info("student: exit\n");
}

module_init(student_init);
module_exit(student_exit);
MODULE_LICENSE("GPL");

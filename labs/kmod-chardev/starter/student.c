#include <linux/fs.h>
#include <linux/module.h>
#include <linux/uaccess.h>

#define CAP 256
/* TODO: khai báo trạng thái của driver: buffer CAP byte, độ dài dữ liệu đang lưu, major number */

static ssize_t dev_read(struct file *f, char __user *ubuf, size_t count, loff_t *ppos)
{
	/* TODO: trả dữ liệu đã lưu cho user-space; nhớ vị trí đọc và báo hết dữ liệu */
	return 0;
}

static ssize_t dev_write(struct file *f, const char __user *ubuf, size_t count, loff_t *ppos)
{
	/* TODO: lưu dữ liệu user-space ghi xuống; count do user quyết định */
	return count;
}

static const struct file_operations fops = {
	.owner = THIS_MODULE,
	.read = dev_read,
	.write = dev_write,
};

static int __init student_init(void)
{
	/* TODO: đăng ký character device tên "student" với major động */
	return 0;
}

static void __exit student_exit(void)
{
	/* TODO: huỷ đăng ký */
}

module_init(student_init);
module_exit(student_exit);
MODULE_LICENSE("GPL");

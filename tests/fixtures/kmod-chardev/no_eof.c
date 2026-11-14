#include <linux/fs.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/uaccess.h>

#define CAP 256
static char data[CAP];
static size_t len;
static int major;
static DEFINE_MUTEX(lock);

static ssize_t dev_read(struct file *f, char __user *ubuf, size_t count, loff_t *ppos)
{
	ssize_t ret;

	mutex_lock(&lock);
	ret = min(count, len);
	if (copy_to_user(ubuf, data, ret))
		ret = -EFAULT;
	mutex_unlock(&lock);
	return ret;
}

static ssize_t dev_write(struct file *f, const char __user *ubuf, size_t count, loff_t *ppos)
{
	if (count > CAP)
		return -EINVAL;
	mutex_lock(&lock);
	if (copy_from_user(data, ubuf, count)) {
		mutex_unlock(&lock);
		return -EFAULT;
	}
	len = count;
	mutex_unlock(&lock);
	return count;
}

static const struct file_operations fops = {
	.owner = THIS_MODULE,
	.read = dev_read,
	.write = dev_write,
};

static int __init student_init(void)
{
	major = register_chrdev(0, "student", &fops);
	return major < 0 ? major : 0;
}

static void __exit student_exit(void)
{
	unregister_chrdev(major, "student");
}

module_init(student_init);
module_exit(student_exit);
MODULE_LICENSE("GPL");

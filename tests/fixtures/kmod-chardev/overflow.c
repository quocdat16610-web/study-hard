#include <linux/fs.h>
#include <linux/module.h>
#include <linux/mutex.h>
#include <linux/slab.h>
#include <linux/uaccess.h>

#define CAP 256
static char *data;
static size_t len;
static int major;
static DEFINE_MUTEX(lock);

static ssize_t dev_read(struct file *f, char __user *ubuf, size_t count, loff_t *ppos)
{
	ssize_t ret;

	mutex_lock(&lock);
	ret = simple_read_from_buffer(ubuf, count, ppos, data, len);
	mutex_unlock(&lock);
	return ret;
}

static ssize_t dev_write(struct file *f, const char __user *ubuf, size_t count, loff_t *ppos)
{
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
	data = kmalloc(CAP, GFP_KERNEL);
	if (!data)
		return -ENOMEM;
	major = register_chrdev(0, "student", &fops);
	return major < 0 ? major : 0;
}

static void __exit student_exit(void)
{
	unregister_chrdev(major, "student");
	kfree(data);
}

module_init(student_init);
module_exit(student_exit);
MODULE_LICENSE("GPL");

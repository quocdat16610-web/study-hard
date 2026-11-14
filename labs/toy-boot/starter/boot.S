.section .multiboot, "a"
.align 4
.long 0x1BADB002, 0, -0x1BADB002

.section .bss
.align 16
stack: .skip 16384
stack_top:

.section .text
.global _start
_start:
	mov $stack_top, %esp
	call kmain
1:	cli
	hlt
	jmp 1b

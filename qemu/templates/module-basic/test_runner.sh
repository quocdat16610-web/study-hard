#!/bin/sh
# Runs INSIDE the guest. One line per test on the serial console:
#   @@GRADER:<nonce>:TEST:<id>:<PASS|FAIL>:<detail>
N=$1 KO=/mnt/student.ko MOD=student
t() {
	id=$1; shift
	if timeout 10 "$@" >/tmp/out 2>&1; then r=PASS; else r=FAIL; fi
	echo "@@GRADER:$N:TEST:$id:$r:$(head -c 160 /tmp/out | tr -c '[:alnum:] _.,=/()-' ' ')"
}
t load     insmod $KO
t listed   grep -q "^$MOD " /proc/modules
t init_log sh -c 'dmesg | grep -q "student: init"'
t license  sh -c '[ "$(cat /proc/sys/kernel/tainted)" = 4096 ]'
t unload   rmmod $MOD
t exit_log sh -c 'dmesg | grep -q "student: exit"'
t clean    sh -c "! grep -q '^$MOD ' /proc/modules"

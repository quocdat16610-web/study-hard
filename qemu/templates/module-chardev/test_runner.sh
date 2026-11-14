#!/bin/sh
# Character-device lab: /dev/student keeps the last write and returns it on read.
N=$1 KO=/mnt/student.ko MOD=student DEV=/dev/student
major() { awk -v m=$MOD '$2 == m { print $1 }' /proc/devices; }
node() { [ -n "$(major)" ] && rm -f $DEV && mknod $DEV c "$(major)" 0; }
rw() { [ -c $DEV ] && printf %s "$1" > $DEV && [ "$(cat $DEV)" = "$1" ]; }
eof() { [ -c $DEV ] && printf abc > $DEV && [ "$(wc -c < $DEV)" = 3 ]; }
big() { [ -c $DEV ] && { head -c 16384 /dev/zero | tr '\0' A > $DEV; rw after-big; }; }
if [ -n "$2" ]; then shift; "$@"; exit $?; fi  # re-entered as a helper so `timeout` can bound it
t() {
	id=$1; shift
	if timeout 3 "$@" >/tmp/out 2>&1; then r=PASS; else r=FAIL; fi
	echo "@@GRADER:$N:TEST:$id:$r:$(head -c 160 /tmp/out | tr -c '[:alnum:] _.,=/()-' ' ')"
}
h() { id=$1; shift; t "$id" sh "$0" "$N" "$@"; killall -q -9 cat wc tr head; }  # a stuck reader must not fail later tests
t load      insmod $KO
t register  grep -q " $MOD\$" /proc/devices
h node      node
h roundtrip rw hello
h overwrite rw x
h eof       eof
h bounds    big
t unload    rmmod $MOD
t cleanup   sh -c "! grep -q ' $MOD\$' /proc/devices"

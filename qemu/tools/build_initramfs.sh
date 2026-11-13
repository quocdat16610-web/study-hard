#!/usr/bin/env bash
# build_initramfs.sh [name] [extra-dir] -> initrds/initramfs-<name>.cpio.gz (needs busybox-static, cpio)
set -euo pipefail
here=$(cd "$(dirname "$0")/.." && pwd)
name=${1:-base} extra=${2:-}
bb=$(command -v busybox)
file -L "$bb" | grep -q 'statically linked' || { echo "busybox must be static" >&2; exit 1; }
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
mkdir -p "$d"/{bin,proc,sys,dev,mnt,tmp}
install -m 0755 "$bb" "$d/bin/busybox"
for a in $("$bb" --list); do [ "$a" = busybox ] || ln -s busybox "$d/bin/$a"; done
install -m 0755 "$here/guest/init" "$d/init"
[ -z "$extra" ] || cp -a "$extra"/. "$d"/
mkdir -p "$here/initrds"
(cd "$d" && find . -mindepth 1 | LC_ALL=C sort | cpio -o -H newc -R 0:0 --quiet | gzip -9n) \
	> "$here/initrds/initramfs-$name.cpio.gz"
ls -l "$here/initrds/initramfs-$name.cpio.gz"

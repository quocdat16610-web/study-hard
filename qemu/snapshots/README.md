Snapshots are VM-state files (`-incoming file:`), not qcow2: `loadvm` needs a writable image,
a state file can be mounted read-only and shared by every run.

    make snapshot TPL=module-basic     # -> <kernel>-<initrd>-<mem>m-<smp>c-<accel>.vmstate

Recreate after ANY change to: kernel, initramfs, QEMU version, host CPU model, vm.mem_mb/smp.
A missing snapshot is not an error: the run cold-boots (slower, same result).

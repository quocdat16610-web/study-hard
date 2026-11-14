"""Kernel-space sandbox: QEMU(+KVM) inside a locked-down container.

The guest is fully untrusted (student code runs in ring 0). The host only ever
reads its serial log; the 9p export is read-only; snapshots are read-only.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from ..config import CFG
from . import serial
from .container import Box, Limits, own

ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
NAME = re.compile(r"[a-z0-9][a-z0-9.-]{0,40}")
ZERO = "0" * 32  # fw_cfg "go" value while the guest must keep waiting (snapshot state)
VM = "/run/vm"
LOG_CAP = 256 << 10
APPEND = "console=ttyS0 loglevel=7 panic=-1 oops=panic softlockup_panic=1 hung_task_panic=1 "\
         "watchdog_thresh=5 rcupdate.rcu_cpu_stall_timeout=10 slub_debug=FZ"


class QMP:
    def __init__(self, path: Path, alive=lambda: True, wait: float = 15):
        end, fd = time.monotonic() + wait, os.open(path.parent, os.O_PATH)  # dodge sun_path's 108 bytes
        try:
            while True:
                self.s = socket.socket(socket.AF_UNIX)
                try:
                    self.s.connect(f"/proc/self/fd/{fd}/{path.name}")
                    break
                except OSError:
                    self.s.close()
                    if time.monotonic() > end or not alive():
                        raise
                    time.sleep(0.05)
        finally:
            os.close(fd)
        self.s.settimeout(30)
        self.r = self.s.makefile("rb")
        self.r.readline()
        self.cmd("qmp_capabilities")

    def cmd(self, name: str, **args):
        self.s.sendall(json.dumps({"execute": name, "arguments": args}).encode() + b"\n")
        while line := self.r.readline():
            msg = json.loads(line)
            if "error" in msg:
                raise RuntimeError(f"qmp {name}: {msg['error']['desc']}")
            if "return" in msg:
                return msg["return"]
        raise ConnectionError("qmp closed")


def _spec(tpl: str) -> tuple[Path, dict]:
    if not NAME.fullmatch(tpl):
        raise ValueError("bad template name")
    d = CFG.qemu_root / "templates" / tpl
    vm = json.loads((d / "expected.json").read_text())["vm"]
    for k in ("kernel", "initrd", "artifact"):
        if k in vm and not NAME.fullmatch(vm[k]):
            raise ValueError(f"bad vm.{k}")
    return d, vm


def _kvm() -> bool:
    if os.access("/dev/kvm", os.R_OK | os.W_OK):
        return True
    if CFG.allow_tcg:
        return False
    raise RuntimeError("KVM unavailable (set GRADER_ALLOW_TCG=1 for dev only)")


def _snap(vm: dict) -> Path:
    accel = "kvm" if _kvm() else "tcg"
    return CFG.qemu_root / "snapshots" / (
        f"{vm['kernel']}-{vm['initrd']}-{vm['mem_mb']}m-{vm.get('smp', 1)}c-{accel}.vmstate")


def _box(vm: dict, rt: Path, nonce: str = ZERO, *, qmp: bool = False, incoming: Path | None = None,
         timeout: float | None = None, fsize_mb: int = 16) -> Box:
    kvm, root, smp = _kvm(), CFG.qemu_root, vm.get("smp", 1)
    a = ["qemu-system-x86_64", *shlex.split((root / "configs/qemu-common.conf").read_text(), comments=True),
         "-machine", f"q35,accel={'kvm' if kvm else 'tcg'}", "-cpu", "host" if kvm else "max",
         "-m", f"{vm['mem_mb']}M", "-smp", str(smp),
         "-chardev", f"file,id=ser,path={VM}/serial.log", "-serial", "chardev:ser"]
    if qmp:
        a += ["-qmp", f"unix:{VM}/qmp.sock,server=on,wait=off"]
    if vm["mode"] == "toy":
        a += ["-kernel", f"{VM}/shared/{vm['artifact']}", "-device", "VGA",
              "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04"]
    else:
        a += ["-kernel", f"/img/kernels/vmlinuz-{vm['kernel']}",
              "-initrd", f"/img/initrds/initramfs-{vm['initrd']}.cpio.gz", "-append", APPEND,
              "-fsdev", f"local,id=sh,path={VM}/shared,security_model=none,readonly=on",
              "-device", "virtio-9p-pci,fsdev=sh,mount_tag=shared",
              "-fw_cfg", f"name=opt/grader/go,string={nonce}"]
    if incoming:
        a += ["-incoming", f"file:/img/snapshots/{incoming.name}"]
    lim = Limits(timeout=timeout or vm.get("timeout", 30), mem_mb=vm["mem_mb"] + 256, cpus=smp,
                 pids=64, fsize_mb=fsize_mb, out_cap=64 << 10)
    mounts = [(rt, VM, True), *((root / n, f"/img/{n}", False) for n in ("kernels", "initrds", "snapshots"))]
    return Box(CFG.qemu_image, a, lim, mounts=mounts, seccomp=root / "configs/seccomp-qemu.json",
               devices=["/dev/kvm"] if kvm else [], groups=[os.stat("/dev/kvm").st_gid] if kvm else [])


def _runtime(sid: str) -> Path:
    if not ID.fullmatch(sid):
        raise ValueError("bad submission id")
    rt = CFG.qemu_root / "runtimes" / sid
    rt.mkdir(mode=0o700)  # FileExistsError on a duplicate id: never share a runtime dir
    (rt / "shared").mkdir()
    return rt


def _drive(box: Box, rt: Path, script: list[dict]) -> bool:
    """Toy kernels: feed keys, dump the VGA text buffer, stop the VM. False if it died early."""
    try:
        q = QMP(rt / "qmp.sock", lambda: box.p.poll() is None)
        for step in script:
            time.sleep(min(float(step.get("wait", 0)), 10))
            for key in step.get("keys", []):
                q.cmd("send-key", keys=[{"type": "qcode", "data": key}])
                time.sleep(0.05)
        q.cmd("pmemsave", val=0xB8000, size=4000, filename=f"{VM}/vga.bin")
        q.cmd("quit")
        return True
    except (OSError, RuntimeError):
        return False


def run(sid: str, tpl: str, artifact: Path) -> dict:
    d, vm = _spec(tpl)
    toy = vm["mode"] == "toy"
    rt = _runtime(sid)
    try:
        with open(os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW), "rb") as src, \
                open(rt / "shared" / vm["artifact"], "wb") as dst:
            shutil.copyfileobj(src, dst)
        if not toy:
            shutil.copyfile(d / "test_runner.sh", rt / "shared/test_runner.sh")
        if (d / "prepare.sh").exists():
            subprocess.run([d / "prepare.sh", rt / "shared"], check=True, timeout=30, cwd=rt)
        own(rt)
        nonce = secrets.token_hex(16)
        snap = None if toy or not _snap(vm).exists() else _snap(vm)
        with _box(vm, rt, nonce, qmp=toy, incoming=snap) as box:
            alive = _drive(box, rt, vm.get("script", [])) if toy else False
            r = box.wait()
        raw = (rt / "serial.log").read_bytes()[-LOG_CAP:] if (rt / "serial.log").exists() else b""
        log = raw.decode("utf-8", "replace")
        out = {"exit_code": r.exit_code, "wall": round(r.wall, 3), "serial": log,
               "qemu_stderr": r.stderr.decode("utf-8", "replace")[-4000:]}
        bad_image = toy and b"kernel" in r.stderr  # QEMU rejected the student's ELF
        if r.exit_code == 1 and r.stderr and not raw and not bad_image:
            out["status"] = "infra_error"  # QEMU never started: not the student's fault
        elif bad_image:
            out["status"] = "bad_image"
        elif toy:
            vga = rt / "vga.bin"
            out |= {"status": "ok" if alive or r.exit_code & 1 else "hang" if r.timed_out else "reset",
                    "vga": serial.vga_text(vga.read_bytes()) if vga.exists() else None}
        else:
            tests, done = serial.parse(log, nonce)
            fail = serial.failure(log)
            out |= {"tests": tests, "failure": fail,
                    "status": "panic" if fail and fail["fatal"] else "ok" if done
                    else "hang" if r.timed_out else "crash"}
        logs = CFG.qemu_root / "logs/qemu"
        logs.mkdir(parents=True, exist_ok=True)
        (logs / f"{sid}.log").write_bytes(raw)
        return out
    finally:
        shutil.rmtree(rt, ignore_errors=True)


def snapshot(tpl: str) -> Path:
    """Boot once, park the guest in its wait loop, save VM state. Runs restore it read-only."""
    _, vm = _spec(tpl)
    if vm["mode"] != "module":
        raise ValueError("snapshots are for module templates")
    dst, rt = _snap(vm), _runtime(f"snap-{secrets.token_hex(4)}")
    try:
        own(rt)
        with _box(vm, rt, qmp=True, timeout=180, fsize_mb=2048) as box:
            q = QMP(rt / "qmp.sock", lambda: box.p.poll() is None)
            end = time.monotonic() + 120
            while b"@@READY" not in ((rt / "serial.log").read_bytes() if (rt / "serial.log").exists() else b""):
                if time.monotonic() > end or box.p.poll() is not None:
                    raise RuntimeError("guest never became ready")
                time.sleep(0.1)
            time.sleep(1)
            q.cmd("migrate", uri=f"file:{VM}/state")
            while (st := q.cmd("query-migrate").get("status")) not in ("completed", "failed"):
                time.sleep(0.05)
            if st != "completed":
                raise RuntimeError("migration failed")
            try:
                q.cmd("quit")
            except (OSError, RuntimeError):
                pass
            box.wait()
        dst.parent.mkdir(exist_ok=True)
        tmp = dst.with_suffix(".tmp")
        shutil.copyfile(rt / "state", tmp)
        os.chmod(tmp, 0o444)
        os.replace(tmp, dst)
        return dst
    finally:
        shutil.rmtree(rt, ignore_errors=True)


def gc(max_age: float = 900) -> list[str]:
    """Remove runtime dirs left behind by a crashed worker."""
    gone = []
    for p in (CFG.qemu_root / "runtimes").glob("*"):
        if time.time() - p.stat().st_mtime > max_age:
            shutil.rmtree(p, ignore_errors=True)
            gone.append(p.name)
    return gone


if __name__ == "__main__":
    op, *arg = sys.argv[1:]
    res = {"run": lambda: run(arg[0], arg[1], Path(arg[2])),
           "snapshot": lambda: str(snapshot(arg[0])), "gc": gc}[op]()
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)

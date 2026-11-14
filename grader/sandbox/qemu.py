"""Kernel-space sandbox: QEMU(+KVM) inside a locked-down container.

The guest is fully untrusted (student code runs in ring 0). The host only ever
reads its serial log; the 9p export is read-only; snapshots are read-only.
"""
from __future__ import annotations

import contextlib
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
from . import image, serial
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
         timeout: float | None = None, fsize_mb: int = 16, cpus: float | None = None) -> Box:
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
    lim = Limits(timeout=timeout or vm.get("timeout", 30), mem_mb=vm["mem_mb"] + 256, cpus=cpus or smp,
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


def _capture(q: QMP, gfx: bool, stem: str) -> None:
    """Text labs: the 80x25 VGA text buffer. Graphics labs: a real screenshot of whatever mode is set."""
    if gfx:
        q.cmd("screendump", filename=f"{VM}/{stem}.ppm")
    else:
        q.cmd("pmemsave", val=0xB8000, size=4000, filename=f"{VM}/{stem}.bin")


def _mouse(q: QMP, dx: int, dy: int) -> None:
    for axis, v in (("x", dx), ("y", dy)):
        while v:  # PS/2 packets carry at most +-127 per axis: feed large moves in pieces
            part = max(-100, min(100, v))
            q.cmd("input-send-event", events=[{"type": "rel", "data": {"axis": axis, "value": part}}])
            v -= part
            time.sleep(0.02)


def _button(q: QMP, button: str, down: bool) -> None:
    q.cmd("input-send-event", events=[{"type": "btn", "data": {"down": down, "button": button}}])


def _drive(box: Box, rt: Path, script: list[dict], gfx: bool) -> bool:
    """Toy kernels: feed keys and mouse input, capture the screen, stop the VM. False if it died early."""
    try:
        q = QMP(rt / "qmp.sock", lambda: box.p.poll() is None)
        for step in script:
            time.sleep(min(float(step.get("wait", 0)), 10))
            for key in step.get("keys", []):
                q.cmd("send-key", keys=[{"type": "qcode", "data": key}])
                time.sleep(0.05)
            if "mouse" in step:
                _mouse(q, int(step["mouse"][0]), int(step["mouse"][1]))
            if "button" in step and step["button"][0] in ("left", "right", "middle"):  # press or release only
                _button(q, step["button"][0], bool(step["button"][1]))
                time.sleep(0.08)
            if step.get("click") in ("left", "right", "middle"):
                _button(q, step["click"], True)
                time.sleep(0.08)
                _button(q, step["click"], False)
            if NAME.fullmatch(step.get("snap", "")):  # mid-script screenshot for multi-step UI tests
                time.sleep(0.3)
                _capture(q, gfx, f"snap-{step['snap']}")
        _capture(q, gfx, "final")
        q.cmd("quit")
        return True
    except (OSError, RuntimeError):
        return False


def _screens(rt: Path, gfx: bool) -> dict:
    """Collect what _drive captured, in the shape the harness and preview expect."""
    def load(p: Path) -> dict | None:
        try:
            if gfx:
                return {"gfx": image.shot(p.read_bytes())}
            raw = p.read_bytes()
            return {"text": serial.vga_text(raw), "attr": serial.vga_attrs(raw)}
        except (OSError, ValueError):
            return None

    ext = "ppm" if gfx else "bin"
    final = load(rt / f"final.{ext}") or {}
    snaps = {p.stem[5:]: s for p in sorted(rt.glob(f"snap-*.{ext}")) if (s := load(p))}
    return {"vga": final.get("text"), "vga_attr": final.get("attr"), "gfx": final.get("gfx"), "snaps": snaps}


def run(sid: str, tpl: str, artifact: Path, script: list[dict] | None = None) -> dict:
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
            alive = _drive(box, rt, script or vm.get("script", []), vm.get("display") == "gfx") if toy else False
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
            out |= {"status": "ok" if alive or r.exit_code & 1 else "hang" if r.timed_out else "reset",
                    **_screens(rt, vm.get("display") == "gfx")}
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


class Live:
    """A running toy kernel the host can look at and type into. No network, no VNC: the screen is
    the VGA text buffer read through QMP, keys go in through QMP."""

    def __init__(self, box: Box, rt: Path, gfx: bool = False):
        self.box, self.rt, self.gfx = box, rt, gfx
        self.q = QMP(rt / "qmp.sock", self.alive)

    def alive(self) -> bool:
        return self.box.p.poll() is None

    def screen(self) -> bytes:
        self.q.cmd("pmemsave", val=0xB8000, size=4000, filename=f"{VM}/vga.bin")
        return (self.rt / "vga.bin").read_bytes()

    def screenshot(self) -> bytes:
        self.q.cmd("screendump", filename=f"{VM}/live.ppm")
        return (self.rt / "live.ppm").read_bytes()

    def move(self, dx: int, dy: int) -> None:
        _mouse(self.q, max(-400, min(400, dx)), max(-400, min(400, dy)))

    def button(self, button: str, down: bool) -> None:
        _button(self.q, button, down)

    def serial(self) -> str:
        f = self.rt / "serial.log"
        return f.read_bytes()[-4000:].decode("utf-8", "replace") if f.exists() else ""

    def press(self, chord: list[str]) -> None:
        self.q.cmd("send-key", keys=[{"type": "qcode", "data": k} for k in chord], **{"hold-time": 30})
        time.sleep(0.04)

    def stop(self) -> None:
        try:
            self.q.cmd("quit")
        except (OSError, RuntimeError):
            pass


@contextlib.contextmanager
def live(sid: str, tpl: str, artifact: Path, seconds: float):
    """Boot a toy kernel and keep it up for at most `seconds`; everything is torn down on exit."""
    _, vm = _spec(tpl)
    if vm["mode"] != "toy":
        raise ValueError("live sessions are for toy kernels")
    rt = _runtime(sid)
    try:
        with open(os.open(artifact, os.O_RDONLY | os.O_NOFOLLOW), "rb") as src, \
                open(rt / "shared" / vm["artifact"], "wb") as dst:
            shutil.copyfileobj(src, dst)
        own(rt)
        with _box(vm, rt, qmp=True, timeout=seconds, cpus=0.5) as box:
            yield Live(box, rt, vm.get("display") == "gfx")
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

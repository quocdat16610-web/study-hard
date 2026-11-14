"""Stage 2: compile service. Compilers always run inside the sandbox — a build is untrusted code too."""
from __future__ import annotations

import os
import shlex
import shutil
import struct
from pathlib import Path

from .config import CFG
from .diag import Diag, Stage, parse
from .sandbox import user
from .sandbox.container import Limits, Result

BUILD = Limits(timeout=60, mem_mb=1536, cpus=2, pids=256, fsize_mb=64, out_cap=256 << 10)
WARN = ["-Wall", "-Wextra", "-Werror", "-fno-color-diagnostics"]
CXX = (".cpp", ".cc", ".cxx")
BARE = ["-ffreestanding", "-fno-exceptions", "-fno-rtti", "-fno-pic", "-fno-stack-protector",
        "-fno-threadsafe-statics", "-fno-use-cxa-atexit", "-mno-sse", "-mno-mmx", "-g"]
TOY = ["-m32", "-O1", *BARE, *WARN]
KCXX = ["-std=c++20", "-O2", *BARE, "-fno-pie", "-mcmodel=kernel", "-mno-red-zone", "-mno-sse2", "-mno-avx",
        "-mno-80387", "-fno-asynchronous-unwind-tables", "-Wall", "-Wextra", "-Werror"]
GPL = {"GPL", "GPL v2", "GPL and additional rights", "Dual BSD/GPL", "Dual MIT/GPL", "Dual MPL/GPL"}
KBUILD = """obj-m := student.o
{objs}ccflags-y := -g -Werror
targets += {cxx}
quiet_cmd_kcxx = CXX [M] $@
      cmd_kcxx = g++ {flags} -I$(src) -c -o $@ $<
$(obj)/%_cxx.o: $(src)/%.cpp FORCE
\t$(call if_changed,kcxx)
"""


def _srcs(work: Path, exts: tuple[str, ...]) -> list[str]:
    return sorted(p.name for p in work.iterdir() if p.suffix in exts)


def _read(path: Path, n: int = -1) -> bytes | None:
    """Read a build product without following symlinks the build may have planted."""
    try:
        with open(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), "rb") as f:
            return f.read(n) if os.fstat(f.fileno()).st_size <= 32 << 20 else None
    except OSError:
        return None


def _stage(r: Result, work: Path, artifact: str, extra: list[Diag] = ()) -> Stage:
    log = (r.stdout + r.stderr).decode("utf-8", "replace")
    diags = [*parse(log), *extra]
    if r.timed_out or r.killed:
        diags.append(Diag("", 0, 0, "error", "", "build-timeout" if r.timed_out else "build-memory"))
    ok = r.exit_code == 0 and _read(work / artifact, 4) is not None and not any(d.severity == "error" for d in diags)
    if not ok and not any(d.severity == "error" for d in diags):
        diags.append(Diag("", 0, 0, "error", log.strip()[-600:], "build-failed"))
    return Stage(ok, diags, {"artifact": artifact, "wall": round(r.wall, 2)}, log[-8000:])


def _fail(rule: str, msg: str) -> Stage:
    return Stage(False, [Diag("", 0, 0, "error", msg, rule)])


def _user(lab: dict, work: Path) -> Stage:
    if not (srcs := _srcs(work, CXX)):
        return _fail("no-sources", "")
    cmd = ["clang++", f"-std={lab.get('std', 'c++20')}", *WARN, "-g", "-O1", "-fno-omit-frame-pointer",
           f"-fsanitize={lab.get('sanitize', 'address,undefined,leak')}", "-o", "prog", *srcs]
    return _stage(user.run(work, cmd, writable=True, lim=BUILD), work, "prog")


def _toy(lab: dict, work: Path) -> Stage:
    cxx, c = _srcs(work, CXX), _srcs(work, (".c", ".S"))
    objs = [Path(f).stem + ".o" for f in cxx + c]
    if not objs or len(set(objs)) != len(objs):
        return _fail("no-sources" if not objs else "duplicate-stem", "")
    shutil.copyfile(lab["tpl_dir"] / "linker.ld", work / "linker.ld")
    steps = [["clang++", f"-std={lab.get('std', 'c++20')}", *TOY, "-c", *cxx]] if cxx else []
    steps += [["clang", *TOY, "-c", *c]] if c else []
    steps.append(["ld.lld", "-m", "elf_i386", "-T", "linker.ld", "-o", "kernel.elf", *objs])
    r = user.run(work, ["sh", "-c", " && ".join(map(shlex.join, steps))], writable=True, lim=BUILD)
    extra, head = [], _read(work / "kernel.elf", 8192) or b""
    if r.exit_code == 0 and not _multiboot(head):
        extra.append(Diag("", 0, 0, "error", "", "multiboot-header"))
    return _stage(r, work, "kernel.elf", extra)


def _multiboot(head: bytes) -> bool:
    """Multiboot 1: magic, flags, checksum (sum == 0), 4-byte aligned, within the first 8 KiB."""
    if head[:6] != b"\x7fELF\x01\x01":
        return False
    for off in range(0, len(head) - 11, 4):
        magic, flags, chk = struct.unpack_from("<III", head, off)
        if magic == 0x1BADB002 and (magic + flags + chk) & 0xFFFFFFFF == 0:
            return True
    return False


def _module(lab: dict, work: Path) -> Stage:
    c, cxx = _srcs(work, (".c",)), _srcs(work, (".cpp",))
    objs = [Path(f).stem + ".o" for f in c] + [Path(f).stem + "_cxx.o" for f in cxx]
    single = c == ["student.c"] and not cxx
    if not objs or (not single and "student.o" in objs):
        return _fail("no-sources" if not objs else "reserved-name", "student.c")
    (work / "Kbuild").write_text(KBUILD.format(
        objs="" if single else f"student-objs := {' '.join(objs)}\n",
        cxx=" ".join(o for o in objs if o.endswith("_cxx.o")), flags=" ".join(KCXX)))
    sh = ("make -s -C /usr/src/linux M=/work modules 2>&1 && echo @@META && modinfo -F vermagic student.ko"
          " && cat /usr/src/linux/include/config/kernel.release && modinfo -F license student.ko")
    r = user.run(work, ["sh", "-c", sh], writable=True, lim=BUILD,
                 image=f"{CFG.kbuild_image}:{lab['vm']['kernel']}")
    extra, out = [], r.stdout.decode("utf-8", "replace")
    if r.exit_code == 0 and "@@META\n" in out:
        vermagic, release, *lic = out.split("@@META\n")[1].splitlines() + [""]
        if vermagic.split()[:1] != [release]:
            raise RuntimeError(f"kbuild image/kernel mismatch: {vermagic!r} vs {release!r}")
        if lic[0] not in GPL:
            file, line = next(((f, i) for f in c + cxx for i, text in
                               enumerate((work / f).read_text(errors="replace").splitlines(), 1)
                               if "MODULE_LICENSE" in text), ("", 0))
            extra.append(Diag(file, line, 0, "error", lic[0], "module-license"))
    st = _stage(r, work, "student.ko", extra)
    st.data["vermagic"] = out.split("@@META\n")[1].splitlines()[0] if "@@META\n" in out else None
    return st


def build(lab: dict, work: Path) -> Stage:
    return {"user": _user, "toy": _toy, "module": _module}[lab["mode"]](lab, work)

"""Hardened `docker run`. Every piece of untrusted code or VM goes through Box."""
from __future__ import annotations

import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from ..config import CFG


@dataclass(frozen=True)
class Limits:
    timeout: float = 10
    mem_mb: int = 256
    cpus: float = 1.0
    pids: int = 64
    fsize_mb: int = 16
    out_cap: int = 1 << 20


@dataclass
class Result:
    exit_code: int
    stdout: bytes
    stderr: bytes
    timed_out: bool
    killed: bool  # SIGKILL before the deadline: OOM or fsize/pids limit
    wall: float


def own(path: Path) -> None:
    """Hand a host dir to the sandbox uid (only needed when the worker runs as root)."""
    if os.getuid() == 0:
        for p in (path, *path.rglob("*")):
            os.chown(p, CFG.uid, CFG.gid, follow_symlinks=False)


class Box:
    def __init__(self, image: str, cmd: list[str], lim: Limits, *,
                 mounts: list[tuple[Path, str, bool]] = (), runtime: str | None = None,
                 seccomp: Path | None = None, devices: list[str] = (), groups: list[int] = (),
                 stdin: bytes = b"", workdir: str = "/"):
        self.name, self.lim, self.stdin = f"g-{uuid.uuid4().hex}", lim, stdin
        a = ["docker", "run", "-i", "--rm", "--name", self.name, "--label", "grader=1",
             "--network=none", "--read-only", "--cap-drop=ALL", "--log-driver=none",
             "--security-opt=no-new-privileges", "--user", f"{CFG.uid}:{CFG.gid}",
             "--pids-limit", str(lim.pids), "--cpus", str(lim.cpus),
             "--memory", f"{lim.mem_mb}m", "--memory-swap", f"{lim.mem_mb}m",
             "--ulimit", "core=0", "--ulimit", "nofile=256:256",
             "--ulimit", f"fsize={lim.fsize_mb << 20}",
             "--tmpfs", "/tmp:rw,nosuid,nodev,noexec,size=64m", "--workdir", workdir]
        for src, dst, rw in mounts:
            src = Path(src).resolve(strict=True)
            if "," in f"{src}{dst}":
                raise ValueError("comma in mount path")
            a += ["--mount", f"type=bind,src={src},dst={dst}" + ("" if rw else ",readonly")]
        if runtime:
            a += ["--runtime", runtime]
        if seccomp:
            a += ["--security-opt", f"seccomp={seccomp}"]
        if CFG.cgroup_parent:
            a += ["--cgroup-parent", CFG.cgroup_parent]
        for d in devices:
            a += ["--device", d]
        for g in groups:
            a += ["--group-add", str(g)]
        self.argv = [*a, image, "timeout", "-s", "KILL", str(lim.timeout), *cmd]

    def __enter__(self) -> Box:
        self.t0 = time.monotonic()
        self.p = subprocess.Popen(self.argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, start_new_session=True)
        self.out, self.err = bytearray(), bytearray()
        self.th = [threading.Thread(target=f, args=a, daemon=True) for f, a in (
            (self._feed, ()), (self._pump, (self.p.stdout, self.out)), (self._pump, (self.p.stderr, self.err)))]
        for t in self.th:
            t.start()
        return self

    def _feed(self) -> None:
        try:
            self.p.stdin.write(self.stdin)
            self.p.stdin.close()
        except OSError:
            pass

    def _pump(self, f, buf: bytearray) -> None:
        while chunk := f.read1(65536):
            buf += chunk[:max(0, self.lim.out_cap - len(buf))]

    def kill(self) -> None:
        subprocess.run(["docker", "rm", "-f", self.name], capture_output=True)

    def wait(self) -> Result:
        late = False
        try:
            code = self.p.wait(self.lim.timeout + 10)
        except subprocess.TimeoutExpired:
            late = True
            self.kill()
            code = self.p.wait()
        wall = time.monotonic() - self.t0
        for t in self.th:
            t.join(5)
        timed_out = late or (code == 137 and wall >= self.lim.timeout)
        return Result(code, bytes(self.out), bytes(self.err), timed_out, code == 137 and not timed_out, wall)

    def __exit__(self, *exc) -> None:
        self.kill()
        self.p.kill()

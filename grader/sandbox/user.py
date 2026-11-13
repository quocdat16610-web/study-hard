"""User-space sandbox: Docker + gVisor. Used for both compiling and running student code."""
from pathlib import Path

from ..config import CFG
from .container import Box, Limits, Result


def run(work: Path, cmd: list[str], *, stdin: bytes = b"", writable: bool = False,
        lim: Limits = Limits()) -> Result:
    with Box(CFG.cpp_image, cmd, lim, mounts=[(work, "/work", writable)],
             runtime=CFG.runtime or None, stdin=stdin, workdir="/work") as box:
        return box.wait()

import os
from dataclasses import dataclass
from pathlib import Path


def _e(key: str, default: str) -> str:
    return os.environ.get(f"GRADER_{key}", default)


@dataclass(frozen=True)
class Config:
    qemu_root: Path = Path(_e("QEMU_ROOT", "/opt/grader/qemu"))
    runtime: str = _e("RUNTIME", "runsc")
    cpp_image: str = _e("CPP_IMAGE", "grader-cpp:latest")
    qemu_image: str = _e("QEMU_IMAGE", "grader-qemu:latest")
    cgroup_parent: str = _e("CGROUP_PARENT", "grader.slice")
    allow_tcg: bool = _e("ALLOW_TCG", "0") == "1"
    uid: int = int(_e("UID", str(os.getuid() or 65534)))
    gid: int = int(_e("GID", str(os.getgid() or 65534)))


CFG = Config()

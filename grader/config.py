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
    labs_root: Path = Path(_e("LABS_ROOT", "/opt/grader/labs"))
    work_root: Path = Path(_e("WORK_ROOT", "/var/lib/grader/work"))
    kbuild_image: str = _e("KBUILD_IMAGE", "grader-kbuild")
    redis_url: str = _e("REDIS_URL", "redis://127.0.0.1:6379/0")
    api_key: str = _e("API_KEY", "")
    worker_id: str = _e("WORKER_ID", os.uname().nodename)
    cgroup_parent: str = _e("CGROUP_PARENT", "grader.slice")
    allow_tcg: bool = _e("ALLOW_TCG", "0") == "1"
    uid: int = int(_e("UID", str(os.getuid() or 65534)))
    gid: int = int(_e("GID", str(os.getgid() or 65534)))


CFG = Config()

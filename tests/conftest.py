import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
os.environ.setdefault("GRADER_QEMU_ROOT", str(ROOT / "qemu"))
os.environ.setdefault("GRADER_LABS_ROOT", str(ROOT / "labs"))
FIX = ROOT / "tests/fixtures"


def _image(name: str) -> bool:
    return bool(shutil.which("docker")) and subprocess.run(
        ["docker", "image", "inspect", name], capture_output=True).returncode == 0


@pytest.fixture(scope="session")
def sandbox(tmp_path_factory):
    """End-to-end tests need the sandbox images; kernel ones also a built guest kernel + initramfs."""
    from grader.config import CFG
    if not _image(CFG.cpp_image):
        pytest.skip("sandbox images not built (make images)")
    work = tmp_path_factory.mktemp("work")
    object.__setattr__(CFG, "work_root", work)
    (CFG.qemu_root / "runtimes").mkdir(exist_ok=True)
    return CFG


@pytest.fixture(scope="session")
def kernel(sandbox):
    k = sandbox.qemu_root / "kernels/vmlinuz-6.6.8-minimal"
    if not (k.exists() and _image(sandbox.qemu_image) and _image(f"{sandbox.kbuild_image}:6.6.8-minimal")):
        pytest.skip("guest kernel / kbuild image not built (make kernel initramfs)")
    return sandbox

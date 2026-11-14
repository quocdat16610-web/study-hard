"""Full pipeline against the reference fixtures. Skipped unless the sandbox images (and kernel) exist."""
import uuid

import pytest

from conftest import FIX
from grader import pipeline


def grade(lab, **files):
    return pipeline.grade({"id": uuid.uuid4().hex, "lab": lab, "files": {n: (FIX / p).read_text() for n, p in files.items()}})


def test_user_good(sandbox):
    r = grade("mem-smartptr", **{"main.cpp": "mem-smartptr/good.cpp"})
    assert r["status"] == "done" and r["score"]["score"] == 100


def test_user_bad_gets_line_accurate_findings_and_low_score(sandbox):
    r = grade("mem-smartptr", **{"main.cpp": "mem-smartptr/bad.cpp"})
    rules = {(d["rule"], d["line"]) for s in r["stages"].values() for d in s["diags"]}
    assert {("rule:no-raw-new", 7), ("rule:unsafe-cstr", 9), ("asan:heap-buffer-overflow", 13)} <= rules
    assert all(t["reason"] == "sanitizer" for t in r["tests"]) and 10 <= r["score"]["score"] <= 20


def test_user_compile_error(sandbox):
    r = grade("mem-smartptr", **{"main.cpp": "mem-smartptr/werror.cpp"})
    assert r["status"] == "compile_error" and r["score"]["score"] == 0
    assert r["stages"]["compile"]["diags"][0]["line"] == 4


def test_rejected_never_reaches_the_compiler(sandbox):
    r = pipeline.grade({"id": uuid.uuid4().hex, "lab": "mem-smartptr",
                        "files": {"main.cpp": 'int main() { system("id"); }\n'}})
    assert r["status"] == "rejected" and list(r["stages"]) == ["precheck"] and r["score"]["score"] == 0


def test_work_dir_is_removed(sandbox):
    grade("mem-smartptr", **{"main.cpp": "mem-smartptr/good.cpp"})
    assert not list(sandbox.work_root.iterdir())


@pytest.mark.parametrize("lab,files", [
    ("kmod-hello", {"student.c": "module-hello/student.c"}),
    ("kmod-cpp-hello", {"student.cpp": "kmod-cpp-hello/student.cpp"}),
    ("kmod-chardev", {"student.c": "kmod-chardev/good.c"}),
    ("toy-boot", {"boot.S": "toy-hello/boot.S", "kernel.cpp": "toy-hello/kernel.cpp"}),
])
def test_kernel_reference_solutions_score_full(kernel, lab, files):
    r = grade(lab, **files)
    assert r["status"] == "done", r.get("error")
    assert r["score"]["score"] == 100, r["tests"]


def test_chardev_partial_credit(kernel):
    r = grade("kmod-chardev", **{"student.c": "kmod-chardev/no_eof.c"})
    by = {t["id"]: t["passed"] for t in r["tests"]}
    assert by["load"] and by["node"] and not by["eof"] and not by["roundtrip"] and by["unload"]
    assert 25 < r["score"]["score"] < 60


def test_chardev_heap_overflow_is_penalised(kernel):
    r = grade("kmod-chardev", **{"student.c": "kmod-chardev/overflow.c"})
    assert r["stages"]["dynamic"]["data"]["failure"]["kind"] == "slab"
    assert r["score"]["penalties"][0]["kind"] == "panic" and r["score"]["score"] <= 55
    assert not list((kernel.qemu_root / "runtimes").iterdir())

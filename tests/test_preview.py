"""Preview (what the student's code showed) and ungraded try-runs."""
import json
import uuid

from conftest import FIX
from grader import feedback, pipeline, preview
from grader.sandbox import serial


def rep(kind, data):
    return {"kind": kind, "stages": {"dynamic": {"data": data}}}


def test_vga_attrs_and_screen_preview():
    raw = b"H\x1fi\x07" + b" \x07" * 1998
    assert serial.vga_attrs(raw)[0][:4] == "1f07" and len(serial.vga_attrs(raw)) == 25
    data = {"status": "ok", "serial": "BOOT\x00 OK\n", "vga": serial.vga_text(raw), "vga_attr": serial.vga_attrs(raw)}
    p = preview.build({"mode": "toy"}, rep("grade", data))
    assert (p["kind"], p["text"][0], p["serial"]) == ("screen", "Hi", "BOOT? OK\n") and len(p["palette"]) == 16
    assert "|Hi" in preview.render(p)


def test_console_preview_hides_grader_protocol():
    log = "boot noise\n@@READY\n[ 1.0] student: init\n@@GRADER:abc:TEST:secret_test:PASS:\n[ 2.0] reboot: Restarting system\n"
    p = preview.build({"mode": "module"}, rep("grade", {"status": "ok", "serial": log}))
    assert p == {"kind": "console", "status": "ok", "log": "[ 1.0] student: init"}


def test_graded_user_runs_expose_no_output():
    run = {"id": "hidden", "stdout": "SECRET", "stderr": "", "exit_code": 0, "timed_out": False, "killed": False}
    assert preview.build({"mode": "user"}, rep("grade", {"runs": [run]})) is None
    assert preview.build({"mode": "user"}, rep("run", {"runs": [run]}))["stdout"] == "SECRET"
    assert preview.build({"mode": "user"}, {"kind": "run", "stages": {}}) is None


def job(lab, **files):
    return {"id": uuid.uuid4().hex, "lab": lab, "files": {n: (FIX / p).read_text() for n, p in files.items()}}


def test_try_run_user_program_with_stdin(sandbox):
    r = pipeline.try_run(job("mem-smartptr", **{"main.cpp": "mem-smartptr/good.cpp"}) | {"stdin": "2\n5 6\n"})
    assert r["kind"] == "run" and "score" not in r and "static" not in r["stages"]
    assert r["preview"]["stdout"] == "6 5\n11\n" and "không chấm điểm" in r["feedback"]["summary"]
    bad = pipeline.try_run(job("mem-smartptr", **{"main.cpp": "mem-smartptr/bad.cpp"}) | {"stdin": "1\n4\n"})
    assert bad["feedback"]["items"][0]["line"] == 13 and bad["feedback"]["retry"]["line"] == 13


def test_try_run_toy_kernel_shows_typed_keys(kernel):
    files = {"boot.S": "toy-hello/boot.S", "kernel.cpp": "toy-hello/kernel.cpp"}
    r = pipeline.try_run(job("toy-boot", **files) | {"keys": ["o", "s", "1"]})
    p = feedback.public(r)["preview"]
    assert p["text"][:2] == ["Hello, kernel", "os1"] and p["serial"] == "BOOT OK\n" and p["attr"][0].startswith("07")
    graded = feedback.public(pipeline.grade(job("toy-boot", **files)))
    assert graded["preview"]["text"][1] == "hi" and graded["score"]["score"] == 100
    assert "stages" not in json.dumps(graded)


def test_try_run_module_shows_kernel_console(kernel):
    r = pipeline.try_run(job("kmod-hello", **{"student.c": "module-hello/student.c"}))
    assert "student: init" in r["preview"]["log"] and "@@GRADER" not in r["preview"]["log"]

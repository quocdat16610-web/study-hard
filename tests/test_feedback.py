"""Feedback engine: catalogue coverage, line accuracy, and what must never reach a student."""
import json

from grader import feedback, harness, precheck, scoring, static
from grader import messages_vi as M
from grader.sandbox import serial

SRC = "#include <linux/module.h>\nstatic int helper(void)\n{\n\treturn 0;\n}\nstatic int __init student_init(void)\n{\n\tint *p = NULL;\n\t*p = 1;\n\treturn helper();\n}\n"


def diag(rule, msg="x", file="main.cpp", line=1, sev="error"):
    return {"file": file, "line": line, "col": 1, "severity": sev, "msg": msg, "rule": rule}


def make(lab, status="done", dynamic=None, **diags):
    st = {k: {"ok": not v, "diags": v, "data": {}} for k, v in ({"precheck": [], "compile": [], "static": []} | diags).items()}
    if status == "rejected":
        st = {"precheck": st["precheck"]}
    if dynamic is not None:
        st["dynamic"] = dynamic
    r = {"id": "s1", "lab": "x", "status": status, "stages": st}
    r["tests"] = harness.evaluate(lab, st.get("dynamic"))
    r["score"] = scoring.score(lab, r, r["tests"])
    return r


def test_every_rule_the_pipeline_can_emit_has_a_specific_message():
    rules = [f"forbidden:{r}" for r in list(precheck.RAW) + [r for m in precheck.CODE.values() for r in m]]
    rules += [f"rule:{r}" for r in static.RULES]
    rules += ["file-count", "too-large", "missing-file", "unexpected-file", "file-name", "encoding", "hidden-unicode",
              "line-limits", "no-sources", "duplicate-stem", "reserved-name", "build-timeout", "build-memory",
              "build-failed", "module-license", "multiboot-header"]
    assert not [r for r in rules if r not in M.RULES]
    assert {k for k, _ in serial.KINDS} | {"hang", "crash", "reset", "bad_image"} <= set(M.KERNEL)
    assert {"wrong-output", "timeout", "memory-limit", "runtime-error", "sanitizer", "failed", "not-run"} <= set(M.REASONS)


def test_catalogue_entries_format_without_errors():
    for entry in [*M.RULES.values(), *(p[2] for p in M.PATTERNS), M.FALLBACK, *M.KERNEL.values()]:
        assert len(entry) == 4 and all(feedback._fill(entry, "m{x}", line="l")[:3])


def test_patterns_pick_the_specific_entry():
    pick = lambda rule, msg: feedback._lookup(rule, msg)[0][0]  # noqa: E731
    assert pick("", "expected ';' after expression") == "Lỗi cú pháp"
    assert pick("-Werror,-Wunused-variable", "unused variable 'x'") == "Khai báo không dùng tới"
    assert pick("link-undefined", "_Znwm") == "Thiếu operator new"
    assert pick("link-undefined", "kmain").startswith("Thiếu điểm vào")
    assert pick("ubsan", "signed integer overflow: 1 + 2") == "Tràn số nguyên có dấu"
    assert pick("clang-analyzer-cplusplus.NewDeleteLeaks", "Potential leak") == "Có thể rò rỉ bộ nhớ"
    assert pick("cppcheck-nullPointer", "Null pointer dereference: p") == "Có thể dùng con trỏ null"
    assert pick("asan:weird-new-kind", "weird") .startswith("Lỗi bộ nhớ")


def test_item_points_at_the_students_line_with_fix_action():
    lab = {"mode": "user", "tests": [{"id": "a", "stdout": "1\n"}]}
    files = {"main.cpp": "int main() {\n    int *a = new int[3];\n}\n"}
    fb = feedback.build(lab, make(lab, static=[diag("rule:no-raw-new", "new", line=2)]), files)
    item = fb["items"][0]
    assert (item["file"], item["line"], item["code"]) == ("main.cpp", 2, "int *a = new int[3];")
    assert item["action"] == {"label": "Thử sửa ngay", "file": "main.cpp", "line": 2, "col": 1} == fb["retry"]
    assert item["hint"] and "make_unique" not in json.dumps(fb, ensure_ascii=False)  # direction, not the answer


def test_compile_error_shows_root_cause_only():
    lab = {"mode": "user", "tests": [{"id": "a", "stdout": "1\n"}]}
    errs = [diag("", f"expected ';' #{i}", line=i) for i in range(1, 9)]
    noise = [diag("clang-analyzer-x", "noise"), diag("rule:unsafe-cstr", "strcpy(", line=3)]
    fb = feedback.build(lab, make(lab, "compile_error", compile=errs, static=noise), {"main.cpp": "a\nb\nc\nd\n"})
    assert [i["stage"] for i in fb["items"]] == ["compile"] * 3 + ["static"]
    assert "main.cpp:1" in fb["next_steps"][0] and len(fb["next_steps"]) == 1


def test_hidden_tests_reveal_nothing():
    lab = {"mode": "user", "tests": [{"id": "h", "stdin": "SECRET-IN", "stdout": "SECRET-OUT\n", "hidden": True},
                                     {"id": "v", "stdin": "7\n", "stdout": "49\n"}]}
    runs = [{"id": i, "stdout": "wrong\n", "exit_code": 0, "timed_out": False, "killed": False, "sanitizer": []} for i in "hv"]
    report = make(lab, dynamic={"ok": False, "diags": [], "data": {"runs": runs}})
    report["feedback"] = feedback.build(lab, report, {"main.cpp": ""})
    text = json.dumps(feedback.public(report), ensure_ascii=False)
    assert "SECRET" not in text and "`49`" in text and "`wrong`" in text


def test_kernel_failure_is_located_in_the_students_function():
    lab = {"mode": "module", "tests": [{"id": "load", "points": 1, "concept": "C"}], "penalties": {"panic": 60}}
    fail = serial.failure("BUG: kernel NULL pointer dereference, address: 0\nRIP: 0010:student_init+0xe/0x20 [student]\n")
    report = make(lab, dynamic={"ok": False, "diags": [], "data": {"status": "panic", "tests": [], "failure": fail}})
    fb = feedback.build(lab, report, {"student.c": SRC})
    item = fb["items"][0]
    assert (item["title"], item["file"], item["line"]) == ("Kernel oops", "student.c", 6) and "student_init" in item["explain"]
    assert fb["tests"][0]["reason"] == "not-run" and fb["tests"][0]["concept"] == "C" and "Bị trừ 60%" in fb["summary"]
    assert feedback._names("_ZN7Greeter4initEv") == ["Greeter", "init"]


def test_public_view_strips_logs_and_infra_details():
    report = {"id": "s", "lab": "x", "status": "infra_error", "error": "RuntimeError: /opt/grader secret path",
              "stages": {"compile": {"log": "RAW LOG"}}}
    report["feedback"] = feedback.build({"mode": "user", "tests": []}, report, {})
    text = json.dumps(feedback.public(report), ensure_ascii=False)
    assert "secret" not in text and "RAW LOG" not in text and "không bị trừ điểm" in text
    assert feedback.public({"id": "s", "status": "queued"})["feedback"]["items"] == []


def test_rejected_and_render():
    lab = {"mode": "user", "tests": [{"id": "a", "stdout": "1\n"}]}
    files = {"main.cpp": 'int main() { system("id"); }\n'}
    fb = feedback.build(lab, make(lab, "rejected", precheck=[diag("forbidden:exec", "system(")]), files)
    out = feedback.render(fb)
    assert "main.cpp:1" in out and "Gợi ý:" in out and "[Thử sửa ngay] -> main.cpp:1" in out and "0/100" in out

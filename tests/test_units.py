"""Pure-logic tests: no Docker, no QEMU."""
import pytest

from grader import harness, labs, precheck, scoring, static
from grader.diag import parse
from grader.dynamic import sanitizer_diags
from grader.sandbox import serial

USER = {"mode": "user", "tests": [{"id": "a", "stdout": "1 2\n3\n", "points": 60}, {"id": "b", "stdout": "x\n", "points": 40}]}


def run(tid, stdout, **kw):
    return {"id": tid, "stdout": stdout, "exit_code": 0, "timed_out": False, "killed": False, "sanitizer": []} | kw


def dyn(*runs):
    return {"ok": True, "diags": [], "data": {"runs": list(runs)}}


@pytest.mark.parametrize("how,exp,got,ok", [
    ("trim", "1 2\n3\n", "1 2  \n3", True), ("trim", "1 2\n", "1  2\n", False),
    ("exact", "a\n", "a", False), ("tokens", "1 2\n3", "1\n2 3\n", True),
    ("float", "0.3333333 ok", "0.33333334 ok", True), ("float", "1.0", "1.1", False),
    ("unordered", "b\na\n", "a\nb\n", True), ("regex", r"pid=\d+", "pid=42\n", True),
])
def test_compare(how, exp, got, ok):
    assert harness.compare(how, exp, got)[0] is ok


def test_compare_reports_first_differing_line():
    ok, d = harness.compare("trim", "a\nb\nc\n", "a\nX\nc\n")
    assert not ok and d["line"] == 2 and d["expected"] == "b" and d["got"] == "X"


def test_user_verdicts_and_partial_credit():
    v = harness.evaluate(USER, dyn(run("a", "1 2\n3\n", exit_code=1, sanitizer=["lsan:detected"]), run("b", "y\n")))
    assert [(t["reason"], t["earned"]) for t in v] == [("sanitizer", 30.0), ("wrong-output", 0.0)]
    v = harness.evaluate(USER, dyn(run("a", "", timed_out=True, exit_code=137), run("b", "", exit_code=139)))
    assert [t["reason"] for t in v] == ["timeout", "runtime-error"] and v[1]["detail"]["signal"] == "SIGSEGV"
    assert all(t["reason"] == "not-run" for t in harness.evaluate(USER, None))


def test_module_and_toy_verdicts():
    lab = {"mode": "module", "tests": [{"id": "load", "points": 1}, {"id": "rw", "points": 1}, {"id": "unload", "points": 1}]}
    data = {"status": "panic", "tests": [{"id": "load", "ok": True, "msg": ""}, {"id": "rw", "ok": False, "msg": "boom"}]}
    assert [t["reason"] for t in harness.evaluate(lab, {"data": data})] == ["ok", "failed", "not-run"]
    toy = {"mode": "toy", "tests": [{"id": "s", "expect": {"serial": "BOOT"}}, {"id": "k", "expect": {"vga": "hi", "row": 1}}]}
    v = harness.evaluate(toy, {"data": {"status": "ok", "serial": "BOOT OK\n", "vga": ["this hi is row 0", ""]}})
    assert [t["passed"] for t in v] == [True, False]


def report(compile_ok=True, diags=(), status="done", dynamic=None):
    st = {"precheck": {"ok": True}, "compile": {"ok": compile_ok}, "static": {"ok": not diags, "diags": list(diags)}}
    if dynamic:
        st["dynamic"] = dynamic
    return {"status": status, "stages": st}


def test_score_weights_and_static_charges():
    full = harness.evaluate(USER, dyn(run("a", "1 2\n3\n"), run("b", "x\n")))
    assert scoring.score(USER, report(), full)["score"] == 100
    half = harness.evaluate(USER, dyn(run("a", "1 2\n3\n"), run("b", "no\n")))
    d = {"rule": "r", "severity": "error", "file": "m.cpp", "line": 1}
    s = scoring.score(USER | {"weights": {"compile": 10, "static": 20, "dynamic": 70}}, report(diags=[d, d, d]), half)
    assert s["components"]["static"]["percent"] == 50  # third repeat of the same rule is free
    assert s["score"] == 10 + 10 + 42
    s = scoring.score(USER | {"static_cost": {"r": 100}}, report(diags=[d]), full)
    assert s["components"]["static"]["earned"] == 0


def test_score_compile_error_rejected_and_penalty():
    none = harness.evaluate(USER, None)
    assert scoring.score(USER, report(compile_ok=False, status="compile_error"), none)["score"] == 0
    assert scoring.score(USER, report(status="rejected"), none)["score"] == 0
    lab = {"mode": "module", "tests": [{"id": "t", "points": 1}], "penalties": {"panic": 60, "warn": 10}}
    data = {"status": "panic", "tests": [{"id": "t", "ok": True, "msg": ""}], "failure": {"kind": "slab", "fatal": True}}
    s = scoring.score(lab, report(dynamic={"data": data}), harness.evaluate(lab, {"data": data}))
    assert s["components"]["dynamic"]["percent"] == 40 and s["penalties"][0]["cause"] == "slab"
    data = {"status": "ok", "tests": [{"id": "t", "ok": True, "msg": ""}], "failure": {"kind": "warn", "fatal": False}}
    assert scoring.score(lab, report(dynamic={"data": data}), harness.evaluate(lab, {"data": data}))["components"]["dynamic"]["percent"] == 90


def test_precheck_blacklist_ignores_comments_and_strings():
    lab = {"mode": "user"}
    src = '// system("x")\nconst char *s = "fork()";\nint main() { system("ls"); }\n'
    d = precheck.check(lab, {"main.cpp": src}).diags
    assert [(x.rule, x.line) for x in d] == [("forbidden:exec", 3)]
    assert precheck.check(lab | {"allow": ["exec"]}, {"main.cpp": src}).ok


@pytest.mark.parametrize("name,text,rule", [
    ("../a.cpp", "", "file-name"), ("a.py", "", "file-name"), ("a.cpp", '#include "/etc/passwd"\n', "forbidden:abs-include"),
    ("a.cpp", "int x; // NOLINT\n", "forbidden:suppress"), ("a.cpp", "int a‮;\n", "hidden-unicode"),
    ("a.cpp", "x\x00y", "encoding"), ("a.cpp", 'const char*m="@@GRADER:x";', "forbidden:grader-marker"),
    ("boot.S", '.incbin "/etc/shadow"\n', "file-name"),
])
def test_precheck_rejects(name, text, rule):
    assert rule in [d.rule for d in precheck.check({"mode": "user"}, {name: text}).diags]


def test_precheck_limits():
    assert "too-large" in [d.rule for d in precheck.check({"mode": "user", "files": {"max_bytes": 10}}, {"a.cpp": "x" * 11}).diags]
    assert "missing-file" in [d.rule for d in precheck.check({"mode": "user", "files": {"required": ["main.cpp"]}}, {"a.cpp": ""}).diags]


def test_custom_rules():
    lab = {"mode": "user", "rules": ["no-raw-new"]}
    src = "struct A { A(const A&) = delete; void* operator new(unsigned long); };\nint main() { int *p = new int; delete p; }\n"
    assert [(d.rule, d.line) for d in static.custom(lab, {"a.cpp": src})] == [("rule:no-raw-new", 2)] * 2
    mod = static.custom({"mode": "module"}, {"s.c": "static double x;\nvoid f(char*d,char*s){ strcpy(d,s); }\n"})
    assert {d.rule for d in mod} == {"rule:kernel-float", "rule:unsafe-cstr"}


def test_diag_parsers():
    log = ("/work/a.cpp:3:5: error: unused variable 'x' [-Werror,-Wunused-variable]\n"
           "b.c:7:20: warning: Null pointer dereference: p [cppcheck-nullPointer]\n"
           'ERROR: modpost: "nope" [/work/student.ko] undefined!\n')
    d = parse(log)
    assert [(x.file, x.line, x.severity) for x in d] == [("a.cpp", 3, "error"), ("b.c", 7, "warning"), ("", 0, "error")]
    assert d[2].rule == "link-undefined" and d[2].msg == "nope"
    asan = ("==7==ERROR: AddressSanitizer: heap-buffer-overflow on address\n"
            "    #0 0x55 in operator new[](unsigned long) /src/asan.cpp:1:1\n    #1 0x55 in main /work/a.cpp:13:16\n"
            "a.cpp:9:3: runtime error: signed integer overflow\n")
    assert [(x.rule, x.line) for x in sanitizer_diags(asan, {"a.cpp"})] == [("ubsan", 9), ("asan:heap-buffer-overflow", 13)]


def test_serial_parsing():
    n = "ab" * 16
    log = (f"@@GRADER:{n}:TEST:load:PASS:\n@@GRADER:{'0' * 32}:TEST:fake:PASS:\n@@GRADER:{n}:TEST:load:FAIL:dup\n"
           "[  1.0] BUG: kernel NULL pointer dereference, address: 0\n[  1.1] RIP: 0010:student_init+0xe/0x20 [student]\n"
           "[  1.2] Kernel panic - not syncing: Fatal exception\n")
    tests, done = serial.parse(log, n)
    assert tests == [{"id": "load", "ok": True, "msg": ""}] and not done
    f = serial.failure(log)
    assert f["kind"] == "oops" and f["fatal"] and f["frames"][0] == {"fn": "student_init", "off": "0xe", "mod": "student"}
    assert serial.failure("WARNING: CPU: 0 PID: 1 at x.c:1\n")["fatal"] is False
    assert serial.failure("BUG kmalloc-256 (Tainted: G O): Redzone overwritten\n")["kind"] == "slab"
    assert serial.vga_text(b"H\x07i\x07" + b" \x07" * 1998)[0] == "Hi"


def test_labs_are_consistent():
    for d in sorted(labs.CFG.labs_root.iterdir()):
        lab = labs.load(d.name)
        ids = [t["id"] for t in lab["tests"]]
        assert len(ids) == len(set(ids)) and all(t.get("points", 1) > 0 for t in lab["tests"])
        assert set(lab.get("rules", [])) <= set(static.RULES)
    with pytest.raises(KeyError):
        labs.load("../etc")

"""Rule-based formative feedback in Vietnamese.

Every item says where (file:line + the student's own line), what, why, and a direction to try —
never the corrected code. Nothing here exposes hidden-test data, raw logs or infrastructure errors.
"""
from __future__ import annotations

import re

from . import messages_vi as M

MAX_ITEMS = 10
MANGLED = {"_Znwm": "operator new(unsigned long)", "_Znam": "operator new[](unsigned long)",
           "_ZdlPv": "operator delete(void*)", "_ZdlPvm": "operator delete(void*, unsigned long)",
           "_ZdaPv": "operator delete[](void*)", "_ZdaPvm": "operator delete[](void*, unsigned long)"}


def _lookup(rule: str, msg: str) -> tuple:
    if rule in M.RULES:
        return M.RULES[rule], ()
    for rx, mx, entry in M.PATTERNS:
        if re.search(rx, rule) and (m := re.search(mx, msg)):
            return entry, tuple(g for g in m.groups() if g)
    return M.FALLBACK, ()


def _fill(entry: tuple, msg: str, groups: tuple = (), **kw) -> list:
    args = (*groups, msg, msg)
    return [s.format(*args, msg=msg, **kw) if s else s for s in entry]


def _code(files: dict[str, str], file: str, line: int) -> str | None:
    lines = files.get(file, "").split("\n")
    return lines[line - 1].strip()[:160] if 0 < line <= len(lines) else None


def _item(stage: str, d: dict, files: dict[str, str]) -> dict:
    msg = MANGLED.get(d["msg"], d["msg"]).replace("/work/", "")[:240]
    entry, groups = _lookup(d["rule"], d["msg"])
    title, explain, hint, concept = _fill(entry, msg, groups)
    file = d["file"] if d["file"] in files else ""
    out = {"stage": stage, "severity": d["severity"], "rule": d["rule"], "file": file, "line": d["line"] if file else 0,
           "col": d["col"] if file else 0, "code": _code(files, file, d["line"]),
           "title": title, "explain": explain, "hint": hint, "concept": concept}
    if file:
        out["action"] = {"label": M.FIX, "file": file, "line": d["line"], "col": d["col"]}
    return out


def _names(symbol: str) -> list[str]:
    """Identifiers inside an Itanium-mangled name (enough to locate the function in the source)."""
    if not symbol.startswith("_Z"):
        return [symbol]
    out, i = [], 2
    while i < len(symbol):
        if m := re.match(r"\d+", symbol[i:]):
            n = int(m.group())
            i += len(m.group())
            out.append(symbol[i:i + n])
            i += n
        else:
            i += 1
    return out or [symbol]


def _locate(fn: str, files: dict[str, str]) -> tuple[str, int]:
    name = _names(fn)[-1]
    for file, text in files.items():
        if m := re.search(rf"^[^\n#/]*\b{re.escape(name)}\s*\([^;{{]*\)[^;{{]*\{{", text, re.M):
            return file, text.count("\n", 0, m.start()) + 1
    return "", 0


def _kernel(dynamic: dict | None, files: dict[str, str]) -> dict | None:
    if not dynamic:
        return None
    data = dynamic["data"]
    fail, status = data.get("failure"), data.get("status")
    key = fail["kind"] if fail else status
    if key not in M.KERNEL:
        return None
    line = re.sub(r"\s+", " ", fail["line"])[:200] if fail else ""
    title, explain, hint, concept = _fill(M.KERNEL[key], line, line=line)
    frame = next((f for f in (fail or {}).get("frames", []) if f["mod"] == "student"), None)
    file, ln = _locate(frame["fn"], files) if frame else ("", 0)
    if frame:
        explain += f" Lỗi phát sinh trong hàm `{'::'.join(_names(frame['fn']))}`."
    out = {"stage": "dynamic", "severity": "error" if not fail or fail["fatal"] else "warning", "rule": f"kernel:{key}",
           "file": file, "line": ln, "col": 0, "code": _code(files, file, ln),
           "title": title, "explain": explain, "hint": hint, "concept": concept}
    if file:
        out["action"] = {"label": M.FIX, "file": file, "line": ln, "col": 0}
    return out


def _test(lab: dict, v: dict, spec: dict) -> dict:
    out = {"id": v["id"], "passed": v["passed"], "earned": v["earned"], "points": v["points"]}
    if v["passed"]:
        return out
    d, reason, hidden = v["detail"] or {}, v["reason"], v["hidden"]
    key = "wrong-output-hidden" if reason == "wrong-output" and hidden else reason
    msg, hint = M.REASONS[key]
    sig = d.get("signal")
    msg = msg.format(limit_s=d.get("limit_s"), limit_mb=d.get("limit_mb"), exit_code=d.get("exit_code"),
                     signal=f", {sig}: {M.SIGNALS.get(sig, 'signal')}" if sig else "",
                     partial=" (output đúng nên được một phần điểm)" if d.get("output_ok") else "")
    if reason == "wrong-output" and not hidden:
        got = "không in gì" if d["got"] is None else f"`{d['got']}`"
        exp = "không còn dòng nào" if d["expected"] is None else f"`{d['expected']}`"
        msg += f" Dòng {d['line']}: mong đợi {exp}, chương trình in {got}."
        if "stdin" in spec:
            out["input"] = spec["stdin"][:200]
    elif reason == "failed" and lab["mode"] == "module" and d.get("msg"):
        msg += (" Thao tác kiểm tra không kết thúc trong thời gian cho phép (bị treo)." if "Terminated" in d["msg"]
                else f" Lệnh kiểm tra báo: `{d['msg'].strip()}`.")
    elif reason == "failed" and lab["mode"] == "toy":
        msg += " Cụ thể: " + "; ".join(M.TOY_MISSED[m] for m in d.get("missed", [])) + "."
        if not hidden and "vga" in d.get("missed", []):
            msg += f" Mong đợi thấy `{spec['expect']['vga']}`, màn hình đang là `{d['screen'].strip()[:80]}`."
    elif reason == "not-run" and d.get("status") in M.KERNEL:
        msg += f" Lý do: {M.KERNEL[d['status']][0].lower()}."
    return out | {"reason": reason, "message": msg, "hint": hint, "concept": v["concept"]}


def _steps(status: str, items: list[dict], tests: list[dict], static_left: int) -> list[str]:
    steps = []
    where = lambda i: f" tại {i['file']}:{i['line']}" if i["file"] else ""  # noqa: E731
    first = {s: next((i for i in items if i["stage"] == s), None) for s in ("precheck", "compile", "dynamic")}
    if first["precheck"]:
        steps.append(f"Xử lý mục bị từ chối: {first['precheck']['title']}{where(first['precheck'])}.")
    elif status == "compile_error" and first["compile"]:
        steps.append(f"Sửa lỗi biên dịch đầu tiên{where(first['compile'])} rồi biên dịch lại trước khi xem các lỗi khác.")
    else:
        if first["dynamic"]:
            steps.append(f"Ưu tiên lỗi khi chạy: {first['dynamic']['title']}{where(first['dynamic'])}.")
        if failed := next((t for t in tests if not t["passed"] and t["reason"] not in ("sanitizer", "not-run")), None):
            steps.append(f"Test `{failed['id']}`: {failed['hint']}")
        if static_left:
            steps.append(f"Xử lý {static_left} phát hiện của phân tích tĩnh để lấy trọn điểm phần static.")
    return steps[:3]


def build(lab: dict, report: dict, files: dict[str, str]) -> dict:
    status, st = report["status"], report["stages"]
    if status == "infra_error":
        return {"summary": M.STATUS["infra_error"], "items": [], "tests": [], "next_steps": [], "retry": None, "more": 0}
    items: list[dict] = []
    for stage in ("precheck", "compile", "dynamic", "static"):
        diags = st.get(stage, {}).get("diags", [])
        if status == "compile_error":  # one root cause at a time; tool noise on broken code is not useful
            diags = diags[:3] if stage == "compile" else [d for d in diags if d["rule"].startswith("rule:")]
        if stage == "static" and (k := _kernel(st.get("dynamic"), files)):
            items.append(k)
        items += [_item(stage, d, files) for d in diags]
    uniq = list({(i["file"], i["line"], i["title"]): i for i in items}.values())
    specs = {t["id"]: t for t in lab["tests"]}
    tests = [_test(lab, v, specs[v["id"]]) for v in report.get("tests", [])]
    score = report["score"]
    lead = M.STATUS.get(status) or M.STATUS["passed" if score["passed"] and not uniq and score["score"] == 100
                                            else "passed" if score["score"] == 100 else "partial"]
    summary = (f"{lead} Điểm: {score['score']:g}/100 ({'đạt' if score['passed'] else 'chưa đạt'}), "
               f"qua {score['tests_passed']}/{score['tests_total']} test.")
    for p in score["penalties"]:
        cause = p["cause"] if p.get("cause") in M.KERNEL else p["kind"]
        summary += f" Bị trừ {p['cost']}% phần chạy thử vì: {M.KERNEL[cause][0].lower()}."
    focus = next((i["action"] for i in uniq if "action" in i), None)
    if focus is None and score["score"] < 100 and files:
        focus = {"label": M.FIX, "file": next(iter(files)), "line": 1, "col": 1}
    return {"summary": summary, "items": uniq[:MAX_ITEMS], "more": max(0, len(uniq) - MAX_ITEMS), "tests": tests,
            "next_steps": _steps(status, uniq, tests, sum(i["stage"] == "static" for i in uniq)), "retry": focus}


def public(report: dict) -> dict:
    """The student-facing view: no logs, no hidden-test data, no infrastructure details."""
    score = report.get("score")
    return {"id": report["id"], "lab": report.get("lab"), "status": report["status"],
            "score": score and {k: score[k] for k in ("score", "max", "passed", "components", "tests_passed", "tests_total")},
            "feedback": report.get("feedback") or {"summary": M.STATUS.get(report["status"], ""), "items": [],
                                                    "tests": [], "next_steps": [], "retry": None, "more": 0}}


def render(fb: dict) -> str:
    """Plain-text rendering for terminals and logs."""
    out = [fb["summary"], ""]
    for i in fb["items"]:
        loc = f"{i['file']}:{i['line']}" if i["file"] else i["stage"]
        out += [f"[{loc}] {i['title']}"] + ([f"    > {i['code']}"] if i["code"] else [])
        out += [f"    {i['explain']}", f"    Gợi ý: {i['hint']}"] + ([f"    Khái niệm: {i['concept']}"] if i["concept"] else [])
    if fb["more"]:
        out.append(f"... và {fb['more']} mục khác.")
    skipped = [t["id"] for t in fb["tests"] if t.get("reason") == "not-run"]
    if skipped:
        out.append(f"[{len(skipped)} test chưa chạy: {', '.join(skipped)}] {M.REASONS['not-run'][1]}")
    for t in fb["tests"]:
        if not t["passed"] and t["reason"] != "not-run":
            out += [f"[test {t['id']}] {t['earned']:g}/{t['points']:g} - {t['message']}", f"    Gợi ý: {t['hint']}"]
            out += [f"    Khái niệm: {t['concept']}"] if t["concept"] else []
    if fb["next_steps"]:
        out += ["", "Việc nên làm tiếp:"] + [f"  {n}. {s}" for n, s in enumerate(fb["next_steps"], 1)]
    if fb["retry"]:
        out.append(f"[{fb['retry']['label']}] -> {fb['retry']['file']}:{fb['retry']['line']}")
    return "\n".join(out)

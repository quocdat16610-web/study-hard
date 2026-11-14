"""Test harness: turn raw dynamic-stage output into one verdict per test (with partial credit)."""
from __future__ import annotations

import re
import signal

SNIP = 200


def _lines(s: str) -> list[str]:
    return [ln.rstrip() for ln in s.replace("\r\n", "\n").rstrip().split("\n")]


def _floats(a: list[str], b: list[str], eps: float) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        try:
            fx, fy = float(x), float(y)
            if abs(fx - fy) > eps * max(1.0, abs(fx)):
                return False
        except ValueError:
            if x != y:
                return False
    return True


def compare(how: str, expected: str, got: str, eps: float = 1e-6) -> tuple[bool, dict | None]:
    """exact | trim (default: ignore trailing blanks) | tokens | float | unordered | regex."""
    if how == "exact":
        ok = expected == got
    elif how == "tokens":
        ok = expected.split() == got.split()
    elif how == "float":
        ok = _floats(expected.split(), got.split(), eps)
    elif how == "unordered":
        ok = sorted(_lines(expected)) == sorted(_lines(got))
    elif how == "regex":
        ok = re.fullmatch(expected, got.strip(), re.S) is not None
    else:
        ok = _lines(expected) == _lines(got)
    if ok:
        return True, None
    exp, out = _lines(expected), _lines(got)
    n = next((i for i, (x, y) in enumerate(zip(exp, out)) if x != y), min(len(exp), len(out)))
    return False, {"line": n + 1, "expected": exp[n][:SNIP] if n < len(exp) else None,
                   "got": out[n][:SNIP] if n < len(out) else None,
                   "expected_lines": len(exp), "got_lines": len(out)}


def _verdict(t: dict, passed: bool, reason: str, detail: dict | None = None, factor: float | None = None) -> dict:
    points = float(t.get("points", 1))
    return {"id": t["id"], "passed": passed, "points": points,
            "earned": round(points * (factor if factor is not None else float(passed)), 2),
            "reason": reason, "detail": detail, "concept": t.get("concept"), "hidden": bool(t.get("hidden"))}


def _user(lab: dict, data: dict) -> list[dict]:
    runs, out = {r["id"]: r for r in data.get("runs", [])}, []
    for t in lab["tests"]:
        r = runs.get(t["id"])
        if r is None:
            out.append(_verdict(t, False, "not-run"))
            continue
        same, diff = compare(t.get("compare", "trim"), t.get("stdout", ""), r["stdout"], t.get("eps", 1e-6))
        if r["timed_out"]:
            v = _verdict(t, False, "timeout", {"limit_s": lab.get("limits", {}).get("timeout", 2)})
        elif r["killed"]:
            v = _verdict(t, False, "memory-limit", {"limit_mb": lab.get("limits", {}).get("mem_mb", 256)})
        elif r["sanitizer"]:  # right answer with a memory/UB bug still earns part of the test
            v = _verdict(t, False, "sanitizer", {"kinds": r["sanitizer"], "output_ok": same},
                         float(lab.get("sanitizer_factor", 0.5)) if same else 0.0)
        elif r["exit_code"] != t.get("exit_code", 0):
            code = r["exit_code"]
            sig = signal.Signals(code - 128).name if 128 < code < 160 and code - 128 in set(signal.Signals) else None
            v = _verdict(t, False, "runtime-error", {"exit_code": code, "signal": sig})
        else:
            v = _verdict(t, same, "ok" if same else "wrong-output", diff)
        out.append(v)
    return out


def _module(lab: dict, data: dict) -> list[dict]:
    seen = {t["id"]: t for t in data.get("tests", [])}
    return [_verdict(t, True, "ok") if seen.get(t["id"], {}).get("ok")
            else _verdict(t, False, "failed", {"msg": seen[t["id"]]["msg"][:SNIP]}) if t["id"] in seen
            else _verdict(t, False, "not-run", {"status": data.get("status")})
            for t in lab["tests"]]


def _toy(lab: dict, data: dict) -> list[dict]:
    serial, vga, out = data.get("serial") or "", data.get("vga") or [], []
    for t in lab["tests"]:
        exp = t.get("expect", {})
        screen = vga[exp["row"]] if "row" in exp and exp["row"] < len(vga) else "\n".join(vga)
        checks = {"serial": exp.get("serial") is None or exp["serial"] in serial,
                  "serial_re": exp.get("serial_re") is None or re.search(exp["serial_re"], serial) is not None,
                  "vga": exp.get("vga") is None or exp["vga"] in screen,
                  "vga_re": exp.get("vga_re") is None or re.search(exp["vga_re"], screen) is not None}
        missed = [k for k, ok in checks.items() if not ok]
        out.append(_verdict(t, not missed, "ok" if not missed else "failed",
                            None if not missed else {"missed": missed, "status": data.get("status"),
                                                     "screen": screen[:SNIP], "serial": serial[-SNIP:]}))
    return out


def evaluate(lab: dict, dynamic: dict | None) -> list[dict]:
    """dynamic = the dynamic Stage as JSON, or None when the pipeline never got that far."""
    if dynamic is None:
        return [_verdict(t, False, "not-run") for t in lab["tests"]]
    return {"user": _user, "module": _module, "toy": _toy}[lab["mode"]](lab, dynamic["data"])

"""What the student's code visibly did: screen + serial (toy kernel), kernel console (module),
stdout (user-space try-run). Student-facing, so graded user-space runs expose nothing (hidden tests)."""
from __future__ import annotations

import re

COLORS = ["#000000", "#0000aa", "#00aa00", "#00aaaa", "#aa0000", "#aa00aa", "#aa5500", "#aaaaaa",
          "#555555", "#5555ff", "#55ff55", "#55ffff", "#ff5555", "#ff55ff", "#ffff55", "#ffffff"]
TAIL = 6000


def _console(serial: str) -> str:
    """Guest console after boot, without the grader's own protocol lines."""
    body = serial.split("@@READY", 1)[-1]
    lines = [ln for ln in body.replace("\r", "").split("\n")
             if "@@GRADER" not in ln and not re.search(r"\] (?:reboot: |ACPI: PM: )", ln)]
    return "\n".join(lines).strip()[-TAIL:]


def build(lab: dict, report: dict) -> dict | None:
    dyn = report["stages"].get("dynamic")
    if not dyn:
        return None
    d, mode = dyn["data"], lab["mode"]
    if mode == "toy" and lab.get("vm", {}).get("display") == "gfx":
        return {"kind": "image", "status": d["status"], "image": d.get("gfx"),
                "serial": re.sub(r"[^\x09\x0a\x20-\x7e]", "?", d["serial"])[-TAIL:]}
    if mode == "toy":
        return {"kind": "screen", "status": d["status"], "cols": 80, "rows": 25, "text": d.get("vga"),
                "attr": d.get("vga_attr"), "palette": COLORS, "serial": re.sub(r"[^\x09\x0a\x20-\x7e]", "?", d["serial"])[-TAIL:]}
    if mode == "module":
        return {"kind": "console", "status": d["status"], "log": _console(d["serial"])}
    if report["kind"] != "run":
        return None
    r = d["runs"][0]
    return {"kind": "program", "exit_code": r["exit_code"], "timed_out": r["timed_out"], "killed": r["killed"],
            "stdout": r["stdout"][-TAIL:], "stderr": r["stderr"].replace("/work/", "")[-TAIL:]}


def render(p: dict | None) -> str:
    """Plain-text rendering (the app draws `text` + `attr` as a coloured 80x25 grid instead)."""
    if p is None:
        return ""
    if p["kind"] == "image":
        size = f"{p['image']['w']}x{p['image']['h']}" if p["image"] else "không chụp được"
        return f"[ảnh màn hình {size}]\nserial: {p['serial'].strip()}"
    if p["kind"] == "screen":
        rows = p["text"] or ["(không lấy được màn hình)"]
        return "\n".join(["+" + "-" * 80 + "+", *(f"|{r:<80}|" for r in rows), "+" + "-" * 80 + "+",
                          f"serial: {p['serial'].strip()}"])
    if p["kind"] == "console":
        return "--- kernel console ---\n" + p["log"]
    return f"--- stdout (exit {p['exit_code']}) ---\n{p['stdout']}" + (f"--- stderr ---\n{p['stderr']}" if p["stderr"] else "")

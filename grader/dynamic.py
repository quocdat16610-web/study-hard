"""Stage 4: execute. User-space tests run one container each; kernel labs boot once in QEMU."""
from __future__ import annotations

import re
from pathlib import Path

from .diag import Diag, Stage
from .sandbox import qemu, user
from .sandbox.container import Limits

CAP = 64 << 10
SAN = re.compile(r"ERROR: (AddressSanitizer|LeakSanitizer): ([\w-]+)|WARNING: (ThreadSanitizer): ([\w -]+?) \(")
FRAME = re.compile(r"#\d+ 0x[0-9a-f]+ in (.+?) /work/([\w.+-]+):(\d+)(?::(\d+))?")
UBSAN = re.compile(r"^(?:/work/)?([\w.+-]+):(\d+):(\d+): runtime error: (.*)$", re.M)


def sanitizer_diags(err: str, files: set[str]) -> list[Diag]:
    """Turn sanitizer reports into diagnostics pinned to the first frame inside student code."""
    out = [Diag(f, int(ln), int(col), "error", msg, "ubsan") for f, ln, col, msg in UBSAN.findall(err)]
    for m in SAN.finditer(err):
        tool, kind = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
        frame = next((f for f in FRAME.finditer(err, m.end()) if f.group(2) in files), None)
        file, line, col = (frame.group(2), int(frame.group(3)), int(frame.group(4) or 0)) if frame else ("", 0, 0)
        rule = {"AddressSanitizer": "asan", "LeakSanitizer": "lsan", "ThreadSanitizer": "tsan"}[tool]
        out.append(Diag(file, line, col, "error", kind.strip().replace(" ", "-"), f"{rule}:{kind.strip().replace(' ', '-')}"))
    return out


def run(lab: dict, work: Path, sid: str, files: set[str]) -> Stage:
    if lab["mode"] != "user":
        res = qemu.run(sid, lab["template"], work / lab["vm"]["artifact"])
        if res["status"] == "infra_error":
            raise RuntimeError(f"qemu: {res['qemu_stderr'][-300:]}")
        return Stage(res["status"] == "ok", [], res)
    lim, runs, diags = Limits(**({"timeout": 2, "pids": 32, "out_cap": CAP} | lab.get("limits", {}))), [], []
    for t in lab["tests"]:
        r = user.run(work, ["./prog", *t.get("args", [])], stdin=t.get("stdin", "").encode(), lim=lim)
        err = r.stderr.decode("utf-8", "replace")
        found = sanitizer_diags(err, files)
        diags += found
        runs.append({"id": t["id"], "exit_code": r.exit_code, "timed_out": r.timed_out, "killed": r.killed,
                     "wall": round(r.wall, 3), "stdout": r.stdout.decode("utf-8", "replace"),
                     "stderr": err[-8000:], "sanitizer": [d.rule for d in found]})
    uniq = list({(d.file, d.line, d.rule): d for d in diags}.values())
    return Stage(all(x["exit_code"] == 0 for x in runs), uniq[:50], {"runs": runs})

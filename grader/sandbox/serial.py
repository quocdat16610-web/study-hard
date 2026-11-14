"""Parse the guest serial log: test results, kernel failures, VGA text dumps."""
from __future__ import annotations

import re
import sys

KINDS = (
    ("kasan", r"BUG: KASAN: [^\r\n]*"),
    ("slab", r"BUG kmalloc[^\r\n]*|BUG [\w-]+ \([^)\r\n]*\): [^\r\n]*"),
    ("lockup", r"watchdog: BUG: soft lockup[^\r\n]*|rcu: INFO: [^\r\n]*stall[^\r\n]*"
               r"|INFO: task [^\r\n]* blocked for more than[^\r\n]*"),
    ("atomic", r"BUG: (?:scheduling while atomic|sleeping function called)[^\r\n]*"),
    ("oops", r"BUG: [^\r\n]*|Oops: [^\r\n]*|general protection fault[^\r\n]*|kernel BUG at [^\r\n]*"
             r"|invalid opcode: [^\r\n]*|divide error: [^\r\n]*"),
    ("panic", r"Kernel panic - not syncing: [^\r\n]*"),
    ("warn", r"WARNING: [^\r\n]*"),
)
FRAME = re.compile(r"(\w+)\+(0x[0-9a-f]+)/0x[0-9a-f]+ \[(\w+)\]")


def parse(log: str, nonce: str) -> tuple[list[dict], bool]:
    tests: dict[str, dict] = {}
    for tid, res, msg in re.findall(rf"@@GRADER:{nonce}:TEST:([\w-]+):(PASS|FAIL):([^\r\n]*)", log):
        tests.setdefault(tid, {"id": tid, "ok": res == "PASS", "msg": msg.strip()})
    return list(tests.values()), f"@@GRADER:{nonce}:DONE" in log


def failure(log: str) -> dict | None:
    """Earliest kernel failure in the log; `fatal` is False for a bare WARNING."""
    hits = []
    for kind, pat in KINDS:
        if m := re.search(pat, log):
            hits.append((m.start(), kind, m.group(0).strip()))
    if not hits:
        return None
    hits.sort(key=lambda h: (h[1] == "warn", h[0]))
    pos, kind, line = hits[0]
    frames = list(dict.fromkeys(FRAME.findall(log[pos:])))[:10]
    return {"kind": kind, "fatal": kind != "warn", "line": line,
            "kinds": sorted({h[1] for h in hits}),
            "frames": [{"fn": f, "off": o, "mod": m} for f, o, m in frames]}


def vga_attrs(raw: bytes) -> list[str]:
    """Attribute byte of each cell (low nibble = foreground, high = background), 160 hex chars per row."""
    return [raw[1:4000:2][i:i + 80].hex() for i in range(0, 2000, 80)]


def vga_text(raw: bytes) -> list[str]:
    chars = raw[0:4000:2].decode("cp437", "replace")
    return [chars[i:i + 80].rstrip("\x00 ") for i in range(0, 2000, 80)]


if __name__ == "__main__":
    import json
    text = open(sys.argv[1], errors="replace").read()
    json.dump({"failure": failure(text), "tests": parse(text, sys.argv[2])[0] if len(sys.argv) > 2 else None},
              sys.stdout, ensure_ascii=False, indent=1)

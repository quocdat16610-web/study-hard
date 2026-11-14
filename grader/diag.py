"""Shared result types: every stage yields a Stage with line-accurate Diags for the feedback engine."""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

SEV = r"fatal error|error|warning|style|performance|portability|information"
LINE = re.compile(rf"^(?:/work/)?([\w.+-]+):(\d+):(?:(\d+):)? ({SEV}): (.*?)(?: \[([\w.,+=:*-]+)\])?$", re.M)
UNDEF = re.compile(r'undefined symbol: (\S+)|"(\S+)" \[[^\]]*\] undefined!|undefined reference to [`\'](\S+?)\'')


@dataclass
class Diag:
    file: str
    line: int
    col: int
    severity: str  # error | warning
    msg: str
    rule: str = ""


@dataclass
class Stage:
    ok: bool
    diags: list[Diag] = field(default_factory=list)
    data: dict = field(default_factory=dict)
    log: str = ""

    def json(self) -> dict:
        return asdict(self)


def parse(log: str, limit: int = 50) -> list[Diag]:
    """clang / gcc / clang-tidy / cppcheck all print `file:line:col: severity: msg [rule]`."""
    out, seen = [], set()
    for f, ln, col, sev, msg, rule in LINE.findall(log):
        d = Diag(f, int(ln), int(col or 0), "error" if "error" in sev else "warning", msg, rule or "")
        if (key := (d.file, d.line, d.rule, d.msg)) not in seen:
            seen.add(key)
            out.append(d)
    for m in UNDEF.finditer(log):
        sym = next(g for g in m.groups() if g)
        if (key := ("", 0, "link-undefined", sym)) not in seen:
            seen.add(key)
            out.append(Diag("", 0, 0, "error", sym, "link-undefined"))
    return out[:limit]

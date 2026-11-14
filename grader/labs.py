"""Lab specs: labs/<id>/lab.json (+ scaffold/). Kernel labs inherit vm/tests from their QEMU template."""
import json
import re

from .config import CFG

NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,40}")


def load(lab_id: str) -> dict:
    if not NAME.fullmatch(lab_id) or not (CFG.labs_root / lab_id / "lab.json").is_file():
        raise KeyError(lab_id)
    d = CFG.labs_root / lab_id
    lab = json.loads((d / "lab.json").read_text()) | {"id": lab_id, "dir": d}
    if lab["mode"] != "user":
        tpl = CFG.qemu_root / "templates" / lab["template"]
        spec = json.loads((tpl / "expected.json").read_text())
        lab["tpl_dir"], lab["vm"] = tpl, spec["vm"]
        lab.setdefault("tests", spec["tests"])
        lab.setdefault("penalties", spec.get("penalties", {}))
    return lab


def scaffold(lab: dict) -> dict[str, bytes]:
    d = lab["dir"] / "scaffold"
    return {p.name: p.read_bytes() for p in sorted(d.iterdir()) if p.is_file()} if d.is_dir() else {}

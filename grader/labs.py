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
        lab["tpl_dir"] = tpl
        lab["vm"] = spec["vm"] | ({"script": lab["script"]} if "script" in lab else {})  # per-lab key script
        lab.setdefault("tests", spec["tests"])
        lab.setdefault("penalties", spec.get("penalties", {}))
    return lab


def listing() -> list[dict]:
    out = []
    for d in sorted(CFG.labs_root.iterdir()):
        if NAME.fullmatch(d.name) and (d / "lab.json").is_file():
            spec = json.loads((d / "lab.json").read_text())
            out.append({"id": d.name, "title": spec.get("title", d.name), "mode": spec["mode"],
                        "track": spec.get("track", ""), "level": spec.get("level", 0)})
    return sorted(out, key=lambda x: (x["track"], x["level"], x["id"]))


def describe(lab_id: str) -> dict:
    """What a client needs to present a lab: statement, expected files, starter code, read-only scaffold."""
    lab = load(lab_id)
    text = lambda sub: {p.name: p.read_text() for p in sorted((lab["dir"] / sub).glob("*")) if p.is_file()}  # noqa: E731
    lesson = lab["dir"] / "lesson.md"
    return {"id": lab_id, "title": lab.get("title", lab_id), "mode": lab["mode"], "statement": lab.get("statement", ""),
            "lesson": lesson.read_text() if lesson.is_file() else "",
            "files": lab.get("files", {}).get("required", []), "starter": text("starter"), "scaffold": text("scaffold"),
            "tests": [{"id": t["id"], "points": t.get("points", 1)} for t in lab["tests"] if not t.get("hidden")]}


def scaffold(lab: dict) -> dict[str, bytes]:
    d = lab["dir"] / "scaffold"
    return {p.name: p.read_bytes() for p in sorted(d.iterdir()) if p.is_file()} if d.is_dir() else {}

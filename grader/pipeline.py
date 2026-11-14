"""One submission, start to finish: pre-check -> compile -> static -> dynamic -> verdicts -> score -> feedback."""
from __future__ import annotations

import json
import logging
import re
import shutil
import sys
from pathlib import Path

from . import compiler, dynamic, feedback, harness, labs, precheck, scoring, static
from .config import CFG
from .sandbox.container import own

ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
log = logging.getLogger("grader")


def grade(sub: dict) -> dict:
    """sub = {"id", "lab", "files": {name: text}} -> report. Never raises for student-caused failures."""
    sid = sub["id"]
    if not ID.fullmatch(sid):
        raise ValueError("bad submission id")
    lab = labs.load(sub["lab"])
    files: dict[str, str] = sub["files"]
    stages: dict = {}
    report = {"id": sid, "lab": lab["id"], "mode": lab["mode"], "status": "done", "stages": stages}
    stages["precheck"] = pre = precheck.check(lab, files)
    if not pre.ok:
        report["status"] = "rejected"
        return _finish(lab, report, files)
    work = CFG.work_root / sid
    work.mkdir(mode=0o700)
    try:
        for name, text in files.items():
            (work / name).write_text(text, encoding="utf-8")
        for name, data in labs.scaffold(lab).items():  # scaffold always wins over a same-named upload
            (work / name).write_bytes(data)
        own(work)
        stages["compile"] = comp = compiler.build(lab, work)
        stages["static"] = static.analyze(lab, work, files)
        if comp.ok:
            stages["dynamic"] = dynamic.run(lab, work, sid, set(files))
        else:
            report["status"] = "compile_error"
    except Exception as e:  # infrastructure, not the student: never scored, never shown verbatim
        log.exception("submission %s failed", sid)
        report |= {"status": "infra_error", "error": f"{type(e).__name__}: {e}"[:500]}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return _finish(lab, report, files)


def _finish(lab: dict, report: dict, files: dict[str, str]) -> dict:
    report["stages"] = {k: v.json() for k, v in report["stages"].items()}
    if report["status"] != "infra_error":  # infrastructure failures are never scored
        report["tests"] = harness.evaluate(lab, report["stages"].get("dynamic"))
        report["score"] = scoring.score(lab, report, report["tests"])
    report["feedback"] = feedback.build(lab, report, files)
    return report


if __name__ == "__main__":  # python -m grader.pipeline [--text] <lab> <file>... : grade locally, no queue
    import uuid
    args = [a for a in sys.argv[1:] if a != "--text"]
    res = grade({"id": uuid.uuid4().hex, "lab": args[0], "files": {Path(p).name: Path(p).read_text() for p in args[1:]}})
    if "--text" in sys.argv:
        print(feedback.render(res["feedback"]))
    else:
        json.dump(res, sys.stdout, ensure_ascii=False, indent=1)

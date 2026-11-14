"""The "Giao diện OS" track: screen-cell checks, snapshots, and every lesson's reference solution."""
import uuid

import pytest

from conftest import FIX
from grader import feedback, harness, labs, pipeline

TRACK = sorted(p.stem for p in (FIX / "ui").glob("ui-*.cpp"))


def shot(rows: dict[int, tuple[str, str]]) -> dict:
    text, attr = [""] * 25, ["07" * 80] * 25
    for r, (t, a) in rows.items():
        text[r], attr[r] = t, (a * 80)[:160]
    return {"text": text, "attr": attr}


def test_cell_checks_compare_text_and_colour():
    s = shot({3: ("  OS", "1e"), 4: ("\x00\x00hi", "07")})
    assert harness._cell(s, {"row": 3, "col": 2, "text": "OS", "attr": "1E"}) is None
    assert harness._cell(s, {"row": 4, "col": 0, "text": "  hi "}) is None  # NUL cells read as blanks
    assert harness._cell(s, {"row": 3, "col": 2, "text": "OS", "attr": "70"})["got_attr"] == "1e"
    assert harness._cell(s, {"row": 3, "col": 2, "text": "os"})["got"] == "OS"
    assert harness._cell(s, {"row": 9, "col": 0, "len": 80, "attr": "07"}) is None


def test_snapshots_select_the_screen_a_test_looks_at():
    lab = {"mode": "toy", "tests": [
        {"id": "early", "points": 1, "expect": {"at": "start", "cells": [{"row": 0, "col": 0, "text": "A"}]}},
        {"id": "late", "points": 1, "expect": {"cells": [{"row": 0, "col": 0, "text": "A"}]}},
        {"id": "gone", "points": 1, "expect": {"at": "missing", "cells": [{"row": 0, "col": 0, "text": "A"}]}}]}
    final = shot({0: ("B", "07")})
    data = {"status": "ok", "serial": "", "vga": final["text"], "vga_attr": final["attr"], "snaps": {"start": shot({0: ("A", "07")})}}
    v = harness.evaluate(lab, {"data": data})
    assert [t["passed"] for t in v] == [True, False, False] and v[1]["detail"]["cell"]["got"] == "B"
    report = {"id": "s", "lab": "x", "status": "done", "kind": "run", "stages": {}, "tests": v}
    msg = feedback.build(lab, report, {})["tests"][1]["message"]
    assert "hàng 0, cột 0" in msg and "`A`" in msg and "`B`" in msg


def test_track_is_listed_in_lesson_order_with_lessons():
    track = [x for x in labs.listing() if x["track"].startswith("Giao diện OS")]
    assert [x["id"] for x in track] == TRACK and [x["level"] for x in track] == list(range(1, len(TRACK) + 1))
    for x in track:
        d = labs.describe(x["id"])
        assert d["lesson"].startswith("# ") and set(d["scaffold"]) == {"boot.S", "ui.h"} and list(d["starter"]) == ["kernel.cpp"]


def grade(lab_id: str, source: str) -> dict:
    return pipeline.grade({"id": uuid.uuid4().hex, "lab": lab_id, "files": {"kernel.cpp": source}})


@pytest.mark.parametrize("lab_id", TRACK)
def test_reference_solution_scores_full_and_starter_does_not(kernel, lab_id):
    good = grade(lab_id, (FIX / "ui" / f"{lab_id}.cpp").read_text())
    assert good["status"] == "done" and good["score"]["score"] == 100, good["tests"]
    start = grade(lab_id, labs.describe(lab_id)["starter"]["kernel.cpp"])
    assert start["status"] == "done" and start["score"]["score"] <= 40, start["tests"]
    assert sum(t["earned"] for t in start["tests"]) <= 20  # the tests measure the student's work, not the scaffold

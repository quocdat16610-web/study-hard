"""Pixel graphics: screenshots, pixel checks, mouse input, and every lesson's reference solution."""
import base64
import threading
import uuid

import pytest

from conftest import FIX
from grader import feedback, harness, labs, live, pipeline, preview
from grader.sandbox import image
from test_live import FakeChannel

TRACK = sorted(p.stem for p in (FIX / "gfx").glob("gfx-*.cpp"))


def canvas(w=8, h=4, colour=(0, 0x80, 0x80), **dots):
    rgb = bytearray(bytes(colour) * (w * h))
    for (x, y), c in dots.get("dots", {}).items():
        rgb[(y * w + x) * 3:(y * w + x) * 3 + 3] = bytes.fromhex(c)
    return {"gfx": image.shot(b"P6\n%d %d\n255\n" % (w, h) + bytes(rgb))}


def test_png_roundtrip_and_ppm_validation():
    rgb = bytes(range(256)) * 3
    assert image.unpng(image.png(16, 16, rgb)) == (16, 16, rgb)
    assert image.png(1, 1, b"\xff\x00\x00")[:8] == b"\x89PNG\r\n\x1a\n"
    for bad in (b"P5\n1 1\n255\n\0", b"P6\n9999 9999\n255\n", b"P6\n2 2\n255\n\0", b""):
        with pytest.raises(ValueError):
            image.ppm(bad)


def test_pixel_rect_bitmap_and_size_checks():
    s = canvas(dots={(1, 1): "ffffff", (2, 1): "ffffff", (1, 2): "ffffff"})
    lab = {"mode": "toy", "tests": [
        {"id": "px", "points": 1, "expect": {"pixels": [{"x": 1, "y": 1, "rgb": "FFFFFF"}, {"x": 0, "y": 0, "rgb": "008080"}]}},
        {"id": "rect", "points": 1, "expect": {"rects": [{"x": 1, "y": 1, "w": 2, "h": 1, "rgb": "ffffff"}]}},
        {"id": "bitmap", "points": 1, "expect": {"bitmaps": [{"x": 1, "y": 1, "rows": ["XX", "X."], "on": "ffffff", "off": "008080"}]}},
        {"id": "wrong", "points": 1, "expect": {"rects": [{"x": 1, "y": 1, "w": 2, "h": 2, "rgb": "ffffff"}]}},
        {"id": "outside", "points": 1, "expect": {"pixels": [{"x": 8, "y": 0, "rgb": "008080"}]}},
        {"id": "size", "points": 1, "expect": {"size": [320, 200]}},
        {"id": "snap", "points": 1, "expect": {"at": "early", "pixels": [{"x": 0, "y": 0, "rgb": "ff0000"}]}}]}
    data = {"status": "ok", "serial": "", "gfx": s["gfx"], "snaps": {"early": canvas(colour=(255, 0, 0))}}
    v = harness.evaluate(lab, {"data": data})
    assert [t["passed"] for t in v] == [True, True, True, False, False, False, True]
    assert v[3]["detail"]["pixel"] == {"x": 2, "y": 2, "expected": "ffffff", "got": "008080"}
    assert v[4]["detail"]["pixel"]["got"] is None and v[5]["detail"]["size"] == [8, 4]
    msgs = [t.get("message", "") for t in feedback.build(lab, {"id": "s", "lab": "x", "status": "done", "kind": "run", "stages": {}, "tests": v}, {})["tests"]]
    assert "chưa bật chế độ đồ hoạ" in msgs[3]  # an 8x4 "screen" means the mode was never switched


def test_pixel_feedback_names_the_pixel_when_the_mode_is_right():
    s = canvas(w=320, h=200)
    lab = {"mode": "toy", "tests": [{"id": "p", "points": 1, "expect": {"pixels": [{"x": 10, "y": 20, "rgb": "ff0000"}]}}]}
    v = harness.evaluate(lab, {"data": {"status": "ok", "serial": "", "gfx": s["gfx"], "snaps": {}}})
    msg = feedback.build(lab, {"id": "s", "lab": "x", "status": "done", "kind": "run", "stages": {}, "tests": v}, {})["tests"][0]["message"]
    assert "(x=10, y=20)" in msg and "#ff0000" in msg and "#008080" in msg


def test_image_preview_and_track_listing():
    lab = {"mode": "toy", "vm": {"display": "gfx"}}
    s = canvas()
    p = preview.build(lab, {"kind": "grade", "stages": {"dynamic": {"data": {"status": "ok", "serial": "GFX OK\n", "gfx": s["gfx"]}}}})
    assert p["kind"] == "image" and p["image"]["w"] == 8 and base64.b64decode(p["image"]["png"])[:4] == b"\x89PNG"
    track = [x["id"] for x in labs.listing() if x["track"] == "Đồ hoạ điểm ảnh"]
    assert track == TRACK
    for lab_id in TRACK:
        d = labs.describe(lab_id)
        assert d["lesson"].startswith("# ") and {"boot.S", "gfx.h"} <= set(d["scaffold"]) and list(d["starter"]) == ["kernel.cpp"]


@pytest.mark.parametrize("event,ok", [("m:5,-3", True), ("m:-400,399", True), ("b:left:1", True), ("b:right:0", True),
                                      ("m:1000,0", False), ("b:left:2", False), ("m:1", False), ("b:nose:1", False)])
def test_pointer_event_names(event, ok):
    assert bool(live.EVENT.fullmatch(event)) is ok


def grade(lab_id: str, source: str) -> dict:
    return pipeline.grade({"id": uuid.uuid4().hex, "lab": lab_id, "files": {"kernel.cpp": source}})


@pytest.mark.parametrize("lab_id", TRACK)
def test_reference_solution_scores_full_and_starter_does_not(kernel, lab_id):
    good = grade(lab_id, (FIX / "gfx" / f"{lab_id}.cpp").read_text())
    assert good["status"] == "done" and good["score"]["score"] == 100, [t for t in good["tests"] if not t["passed"]]
    shot = feedback.public(good)["preview"]["image"]
    assert (shot["w"], shot["h"]) == (320, 200)
    start = grade(lab_id, labs.describe(lab_id)["starter"]["kernel.cpp"])
    assert start["status"] == "done" and start["score"]["score"] <= 40, start["tests"]
    assert sum(t["earned"] for t in start["tests"]) <= 20


def test_live_graphics_session_streams_screenshots_and_takes_mouse_input(kernel):
    ch = FakeChannel()
    sub = {"id": uuid.uuid4().hex, "lab": "gfx-05-mouse", "files": {"kernel.cpp": (FIX / "gfx/gfx-05-mouse.cpp").read_text()}}
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("reason", live.session(sub, ch)))
    t.start()

    def cursor_at(x, y):
        def pred(f):
            if f["state"] != "running" or "image" not in f or f["image"]["w"] != 320:
                return False
            _, _, rgb = image.pixels(f["image"])
            return rgb[(y * 320 + x) * 3:(y * 320 + x) * 3 + 3] == b"\xff\xff\xff"
        return pred

    ch.wait(cursor_at(160, 100))
    ch.pending = ["m:-30,-20"]
    ch.wait(cursor_at(130, 80))
    ch.pending = ["m:20,5", "b:left:1", "b:left:0", "m:10,5"]
    ch.wait(cursor_at(160, 90))
    ch.stop = True
    t.join(20)
    assert result["reason"] == "stopped" and "text" not in ch.frames[-1]

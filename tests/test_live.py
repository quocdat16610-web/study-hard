"""Live sessions: stream the toy kernel's screen, type into it, always clean up."""
import threading
import time
import uuid

import pytest

from conftest import FIX
from grader import live


class FakeChannel:
    def __init__(self):
        self.frames, self.pending, self.stop, self.watching = [], [], False, True

    def publish(self, frame): self.frames.append(frame)
    def keys(self): out, self.pending = self.pending, []; return out
    def watched(self): return self.watching
    def stopped(self): return self.stop

    def wait(self, pred, secs=40):
        end = time.time() + secs
        while time.time() < end:
            if any(pred(f) for f in self.frames):
                return
            time.sleep(0.1)
        raise AssertionError(f"no matching frame; last: {self.frames[-1] if self.frames else None}")


def toy(kernel="toy-hello/kernel.cpp"):
    return {"id": uuid.uuid4().hex, "lab": "toy-boot",
            "files": {"boot.S": (FIX / "toy-hello/boot.S").read_text(), "kernel.cpp": (FIX / kernel).read_text()}}


@pytest.mark.parametrize("key,ok", [("a", True), ("shift+a", True), ("ctrl+alt+delete", True), ("ret", True),
                                    ("A", False), ("a;b", False), ("shift+", False), ("x" * 17, False)])
def test_key_names(key, ok):
    assert bool(live.KEY.fullmatch(key)) is ok


def test_live_session_streams_screen_and_accepts_keys(kernel):
    ch, sub = FakeChannel(), toy()
    result = {}
    t = threading.Thread(target=lambda: result.setdefault("reason", live.session(sub, ch)))
    t.start()
    ch.wait(lambda f: f["state"] == "running" and f["text"][0] == "Hello, kernel" and "BOOT OK" in f["serial"])
    ch.pending = ["l", "i", "v", "e", "shift+x"]
    ch.wait(lambda f: f["state"] == "running" and f["text"][1] == "livex")
    seqs = [f["seq"] for f in ch.frames]
    assert seqs == sorted(set(seqs)) and ch.frames[0]["state"] == "building" and len(ch.frames) < 30  # only on change
    ch.stop = True
    t.join(20)
    assert result["reason"] == "stopped" and ch.frames[-1]["state"] == "ended" and ch.frames[-1]["text"][1] == "livex"
    assert not (kernel.qemu_root / "runtimes" / sub["id"]).exists() and not (kernel.work_root / sub["id"]).exists()


def test_live_session_stops_when_nobody_watches(kernel, monkeypatch):
    monkeypatch.setattr(live, "IDLE_GRACE", 2)
    ch = FakeChannel()
    ch.watching = False
    assert live.session(toy(), ch) == "idle"


def test_live_session_time_limit(kernel):
    old = live.CFG.live_seconds
    object.__setattr__(live.CFG, "live_seconds", 3)  # frozen dataclass
    try:
        ch, t0 = FakeChannel(), time.time()
        assert live.session(toy(), ch) == "timeout" and ch.frames[-1]["reason"] == "timeout"
        assert time.time() - t0 < 30
    finally:
        object.__setattr__(live.CFG, "live_seconds", old)


def test_live_compile_error_returns_feedback_and_never_boots(kernel):
    sub = toy()
    sub["files"]["kernel.cpp"] = "extern \"C\" void kmain() { int x }\n"
    ch = FakeChannel()
    assert live.session(sub, ch) == "compile_error"
    end = ch.frames[-1]
    assert end["feedback"]["items"][0]["file"] == "kernel.cpp" and all(f["state"] != "running" for f in ch.frames)
    sub = toy()
    sub["files"]["kernel.cpp"] += '\nconst char *leak = "@@GRADER";\n'
    assert live.session(sub, FakeChannel()) == "rejected"


def test_live_refuses_non_toy_labs(sandbox):
    ch = FakeChannel()
    assert live.session({"id": uuid.uuid4().hex, "lab": "mem-smartptr", "files": {"main.cpp": ""}}, ch) == "unsupported"

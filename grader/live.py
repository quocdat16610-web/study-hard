"""Live sessions: a student's toy kernel stays up for a couple of minutes while the browser watches
its screen and types into it.

The sandbox is unchanged (no network, no VNC). This process polls the VM's text screen and serial
log, publishes a frame whenever they change, and forwards queued key presses.
"""
from __future__ import annotations

import json
import logging
import re
import signal
import threading
import time
from typing import Protocol

from . import compiler, feedback, labs, pipeline, precheck, preview, queue as q
from .config import CFG
from .sandbox import qemu, serial

log = logging.getLogger("grader.live")
KEY = re.compile(r"(?:(?:shift|ctrl|alt)\+){0,3}[a-z0-9_]{1,16}")
TICK = 0.1
IDLE_GRACE = 8  # seconds without a watching client before the VM is stopped


class Channel(Protocol):
    def publish(self, frame: dict) -> None: ...
    def keys(self) -> list[str]: ...
    def watched(self) -> bool: ...
    def stopped(self) -> bool: ...


class RedisChannel:
    def __init__(self, r, sid: str):
        self.r, self.sid = r, sid

    def publish(self, frame: dict) -> None:
        self.r.set(q.live(self.sid, "frame"), json.dumps(frame, ensure_ascii=False), ex=600)

    def keys(self) -> list[str]:
        return self.r.lpop(q.live(self.sid, "keys"), 8) or []

    def watched(self) -> bool:
        return bool(self.r.exists(q.live(self.sid, "seen")))

    def stopped(self) -> bool:
        return bool(self.r.exists(q.live(self.sid, "stop")))


def session(sub: dict, ch: Channel, halt: threading.Event | None = None) -> str:
    """Build, boot, stream until the time is up / nobody watches / stop requested / the VM dies."""
    sid, files, seq = sub["id"], sub["files"], 0
    lab = labs.load(sub["lab"])

    def emit(state: str, **extra) -> None:
        nonlocal seq
        seq += 1
        ch.publish({"id": sid, "seq": seq, "state": state} | extra)

    if lab["mode"] != "toy":
        emit("ended", reason="unsupported")
        return "unsupported"
    emit("building")
    report = {"id": sid, "lab": lab["id"], "mode": "toy", "kind": "run", "status": "done", "stages": {}}
    stages = report["stages"]
    stages["precheck"] = precheck.check(lab, files).json()
    reason, last = "rejected", {}
    try:
        if stages["precheck"]["ok"]:
            with pipeline.workspace(sid, lab, files) as work:
                stages["compile"] = compiler.build(lab, work).json()
                reason = "compile_error"
                if stages["compile"]["ok"]:
                    reason, last = _stream(sid, lab, work, ch, emit, halt)
        if reason in ("rejected", "compile_error"):
            report["status"] = reason
            last = {"feedback": feedback.build(lab, report, files)}
    except Exception:  # infrastructure: say so, never leak details
        log.exception("live session %s", sid)
        reason, last = "infra_error", {}
    emit("ended", reason=reason, **last)
    return reason


def _stream(sid: str, lab: dict, work, ch: Channel, emit, halt) -> tuple[str, dict]:
    shown, frame, t0 = None, {}, time.monotonic()
    with qemu.live(sid, lab["template"], work / lab["vm"]["artifact"], CFG.live_seconds + 5) as vm:
        try:
            while True:
                left = CFG.live_seconds - (time.monotonic() - t0)
                if left <= 0:
                    return "timeout", frame
                if ch.stopped() or (halt is not None and halt.is_set()):
                    return "stopped", frame
                if time.monotonic() - t0 > IDLE_GRACE and not ch.watched():
                    return "idle", frame
                for key in ch.keys():
                    if KEY.fullmatch(key):
                        vm.press(key.split("+"))
                raw, out = vm.screen(), vm.serial()
                if (raw, out) != shown:
                    shown = (raw, out)
                    frame = {"cols": 80, "rows": 25, "text": serial.vga_text(raw), "attr": serial.vga_attrs(raw),
                             "palette": preview.COLORS, "serial": re.sub(r"[^\x09\x0a\x20-\x7e]", "?", out)}
                    emit("running", left=int(left), **frame)
                time.sleep(TICK)
        except (OSError, RuntimeError):  # QMP gone: the guest reset (triple fault) or QEMU was killed
            return "reset", frame
        finally:
            vm.stop()


def main() -> None:
    import redis
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    r = redis.Redis.from_url(CFG.redis_url, decode_responses=True)
    slots, halt = threading.Semaphore(CFG.live_max), threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: halt.set())
    qemu.gc()

    def serve(sid: str, raw: str) -> None:
        try:
            log.info("live %s -> %s", sid, session(json.loads(raw) | {"id": sid}, RedisChannel(r, sid), halt))
        except Exception:
            log.exception("live %s", sid)
        finally:
            slots.release()

    log.info("live worker ready: %d slots, %ds each", CFG.live_max, CFG.live_seconds)
    threads: list[threading.Thread] = []
    while not halt.is_set():
        if not slots.acquire(timeout=1):
            continue
        item = r.brpop(q.LIVE_QUEUE, 1)
        raw = item and r.getdel(q.job(item[1]))
        if not raw:
            slots.release()
            continue
        threads = [t for t in threads if t.is_alive()] + [threading.Thread(target=serve, args=(item[1], raw))]
        threads[-1].start()
    for t in threads:
        t.join(15)


if __name__ == "__main__":
    main()

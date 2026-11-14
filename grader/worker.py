"""Queue consumer: one submission at a time per process. Scale by running more workers."""
from __future__ import annotations

import json
import logging
import shutil
import signal
import time

import redis

from . import pipeline, queue as q
from .config import CFG
from .sandbox import qemu

log = logging.getLogger("grader.worker")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    r = redis.Redis.from_url(CFG.redis_url, decode_responses=True)
    mine, stop = q.processing(CFG.worker_id), []
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.append(1))  # finish the current job, then exit
    while sid := r.lmove(mine, q.QUEUE, "RIGHT", "RIGHT"):  # a previous run of this worker died mid-job
        if pipeline.ID.fullmatch(sid):
            for stale in (CFG.work_root / sid, CFG.qemu_root / "runtimes" / sid):
                shutil.rmtree(stale, ignore_errors=True)
    qemu.gc()
    for stale in CFG.work_root.glob("*"):
        if time.time() - stale.stat().st_mtime > 900:
            shutil.rmtree(stale, ignore_errors=True)
    log.info("worker %s ready", CFG.worker_id)
    while not stop:
        if not (sid := r.blmove(q.QUEUE, mine, 2, "RIGHT", "LEFT")):
            continue
        try:
            raw = r.get(q.job(sid))
            if raw is None:
                continue  # expired while queued
            if r.incr(q.tries(sid)) > q.MAX_TRIES:  # it already took a worker down: do not loop on it
                report = {"id": sid, "status": "infra_error", "error": "worker crashed repeatedly"}
            else:
                r.expire(q.tries(sid), q.TTL)
                r.set(q.result(sid), json.dumps({"id": sid, "status": "running"}), ex=q.TTL)
                try:
                    report = pipeline.grade(json.loads(raw) | {"id": sid})
                except Exception as e:
                    log.exception("job %s", sid)
                    report = {"id": sid, "status": "infra_error", "error": type(e).__name__}
            r.set(q.result(sid), json.dumps(report, ensure_ascii=False), ex=q.TTL)
            r.delete(q.job(sid))
            log.info("job %s -> %s", sid, report["status"])
        finally:
            r.lrem(mine, 1, sid)


if __name__ == "__main__":
    main()

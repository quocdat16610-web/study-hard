"""Submission API. It only validates and enqueues; it never touches student code."""
from __future__ import annotations

import asyncio
import json
import secrets
import uuid
from typing import Annotated

import redis.asyncio as redis
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, StringConstraints

from . import feedback, labs, pipeline, queue as q
from .config import CFG

MAX_BODY = 1 << 20
if not CFG.api_key:
    raise RuntimeError("GRADER_API_KEY must be set")
app = FastAPI(title="grader", docs_url=None, redoc_url=None, openapi_url=None)
db = redis.Redis.from_url(CFG.redis_url, decode_responses=True)


CSP = "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers.update({"Content-Security-Policy": CSP, "X-Content-Type-Options": "nosniff",
                         "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})
    return resp


@app.get("/", include_in_schema=False)
async def index() -> RedirectResponse:
    return RedirectResponse("/ui/")


class Submission(BaseModel):
    lab: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,40}$")]
    files: dict[Annotated[str, StringConstraints(max_length=70)],
                Annotated[str, StringConstraints(max_length=256 << 10)]] = Field(min_length=1, max_length=8)


class Run(Submission):
    """Ungraded try-run: optional stdin (user-space) or keys typed into the toy kernel after boot."""
    stdin: Annotated[str, StringConstraints(max_length=64 << 10)] = ""
    keys: list[Annotated[str, StringConstraints(pattern=r"^[a-z0-9_]{1,16}$")]] = Field(default=[], max_length=64)


class Keys(BaseModel):
    keys: list[Annotated[str, StringConstraints(pattern=r"^(?:(?:shift|ctrl|alt)\+){0,3}[a-z0-9_]{1,16}$")]] = Field(
        min_length=1, max_length=32)


async def guard(request: Request, x_api_key: Annotated[str, Header()] = "") -> None:
    if not secrets.compare_digest(x_api_key.encode(), CFG.api_key.encode()):
        raise HTTPException(401)
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise HTTPException(413)


@app.get("/labs", dependencies=[Depends(guard)])
async def list_labs() -> list[dict]:
    return labs.listing()


@app.get("/labs/{lab_id}", dependencies=[Depends(guard)])
async def get_lab(lab_id: str) -> dict:
    try:
        return labs.describe(lab_id)
    except KeyError:
        raise HTTPException(404, "unknown lab") from None


@app.post("/submissions", status_code=202, dependencies=[Depends(guard)])
async def submit(sub: Submission) -> dict:
    return await _enqueue(sub, q.QUEUE, "grade")


@app.post("/runs", status_code=202, dependencies=[Depends(guard)])
async def run(sub: Run) -> dict:
    """Build and execute once without grading; poll GET /submissions/{id} for `preview`."""
    return await _enqueue(sub, q.RUN_QUEUE, "run")


async def _enqueue(sub: Submission, queue: str, kind: str) -> dict:
    try:
        labs.load(sub.lab)
    except KeyError:
        raise HTTPException(404, "unknown lab") from None
    if await db.llen(queue) >= q.MAX_QUEUED:
        raise HTTPException(503, "queue full", headers={"Retry-After": "30"})
    sid = uuid.uuid4().hex
    async with db.pipeline(transaction=True) as tx:
        tx.set(q.job(sid), json.dumps(sub.model_dump() | {"kind": kind}), ex=q.TTL)
        tx.set(q.result(sid), json.dumps({"id": sid, "status": "queued"}), ex=q.TTL)
        tx.lpush(queue, sid)
        await tx.execute()
    return {"id": sid, "status": "queued"}


@app.post("/live", status_code=202, dependencies=[Depends(guard)])
async def live_start(sub: Submission) -> dict:
    """Boot a toy kernel and keep it running; watch it with GET /live/{id}, type with POST /live/{id}/keys."""
    try:
        if labs.load(sub.lab)["mode"] != "toy":
            raise HTTPException(400, "live sessions are for toy-kernel labs")
    except KeyError:
        raise HTTPException(404, "unknown lab") from None
    if await db.llen(q.LIVE_QUEUE) >= CFG.live_max:
        raise HTTPException(503, "no live slot free", headers={"Retry-After": "15"})
    sid = uuid.uuid4().hex
    async with db.pipeline(transaction=True) as tx:
        tx.set(q.job(sid), sub.model_dump_json(), ex=300)
        tx.set(q.live(sid, "frame"), json.dumps({"id": sid, "seq": 0, "state": "queued"}), ex=600)
        tx.set(q.live(sid, "seen"), 1, ex=30)
        tx.lpush(q.LIVE_QUEUE, sid)
        await tx.execute()
    return {"id": sid, "state": "queued", "max_seconds": CFG.live_seconds}


@app.get("/live/{sid}", dependencies=[Depends(guard)])
async def live_frame(sid: str, after: int = -1) -> dict:
    """Long-poll: returns as soon as there is a frame newer than `after` (or after ~2 s with the same one).
    Polling is also the heartbeat: a session nobody polls is stopped."""
    if not pipeline.ID.fullmatch(sid):
        raise HTTPException(404)
    for _ in range(20):
        raw = await db.get(q.live(sid, "frame"))
        if raw is None:
            raise HTTPException(404)
        frame = json.loads(raw)
        await db.set(q.live(sid, "seen"), 1, ex=8)
        if frame["seq"] > after or frame["state"] == "ended":
            break
        await asyncio.sleep(0.1)
    return frame


@app.post("/live/{sid}/keys", status_code=202, dependencies=[Depends(guard)])
async def live_keys(sid: str, body: Keys) -> dict:
    if not pipeline.ID.fullmatch(sid) or not await db.exists(q.live(sid, "frame")):
        raise HTTPException(404)
    if await db.llen(q.live(sid, "keys")) > 256:
        raise HTTPException(429)
    async with db.pipeline(transaction=True) as tx:
        tx.rpush(q.live(sid, "keys"), *body.keys)
        tx.expire(q.live(sid, "keys"), 60)
        await tx.execute()
    return {"queued": len(body.keys)}


@app.delete("/live/{sid}", status_code=202, dependencies=[Depends(guard)])
async def live_stop(sid: str) -> dict:
    if not pipeline.ID.fullmatch(sid) or not await db.exists(q.live(sid, "frame")):
        raise HTTPException(404)
    await db.set(q.live(sid, "stop"), 1, ex=600)
    return {"state": "stopping"}


@app.get("/submissions/{sid}", dependencies=[Depends(guard)])
async def status(sid: str) -> dict:
    if not pipeline.ID.fullmatch(sid) or (raw := await db.get(q.result(sid))) is None:
        raise HTTPException(404)
    return feedback.public(json.loads(raw))


@app.get("/submissions/{sid}/report", dependencies=[Depends(guard)])
async def full_report(sid: str) -> dict:
    """Instructor view: every stage, log and raw run. Never forward this to students."""
    if not pipeline.ID.fullmatch(sid) or (raw := await db.get(q.result(sid))) is None:
        raise HTTPException(404)
    return json.loads(raw)


# Minimal demo UI (static files only; every data call above still needs the API key).
app.mount("/ui", StaticFiles(directory=Path(__file__).parent / "web", html=True), name="ui")

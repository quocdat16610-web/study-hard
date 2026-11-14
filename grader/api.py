"""Submission API. It only validates and enqueues; it never touches student code."""
from __future__ import annotations

import json
import secrets
import uuid
from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field, StringConstraints

from . import feedback, labs, pipeline, queue as q
from .config import CFG

MAX_BODY = 1 << 20
if not CFG.api_key:
    raise RuntimeError("GRADER_API_KEY must be set")
app = FastAPI(title="grader", docs_url=None, redoc_url=None, openapi_url=None)
db = redis.Redis.from_url(CFG.redis_url, decode_responses=True)


class Submission(BaseModel):
    lab: Annotated[str, StringConstraints(pattern=r"^[a-z0-9][a-z0-9-]{0,40}$")]
    files: dict[Annotated[str, StringConstraints(max_length=70)],
                Annotated[str, StringConstraints(max_length=256 << 10)]] = Field(min_length=1, max_length=8)


async def guard(request: Request, x_api_key: Annotated[str, Header()] = "") -> None:
    if not secrets.compare_digest(x_api_key.encode(), CFG.api_key.encode()):
        raise HTTPException(401)
    if int(request.headers.get("content-length") or 0) > MAX_BODY:
        raise HTTPException(413)


@app.post("/submissions", status_code=202, dependencies=[Depends(guard)])
async def submit(sub: Submission) -> dict:
    try:
        labs.load(sub.lab)
    except KeyError:
        raise HTTPException(404, "unknown lab") from None
    if await db.llen(q.QUEUE) >= q.MAX_QUEUED:
        raise HTTPException(503, "queue full", headers={"Retry-After": "30"})
    sid = uuid.uuid4().hex
    async with db.pipeline(transaction=True) as tx:
        tx.set(q.job(sid), sub.model_dump_json(), ex=q.TTL)
        tx.set(q.result(sid), json.dumps({"id": sid, "status": "queued"}), ex=q.TTL)
        tx.lpush(q.QUEUE, sid)
        await tx.execute()
    return {"id": sid, "status": "queued"}


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

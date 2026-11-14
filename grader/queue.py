"""Redis keys shared by API and worker. Queue holds ids only; payloads and results expire on their own."""
QUEUE = "grader:queue"
RUN_QUEUE = "grader:queue:run"  # try-runs: interactive, served first
LIVE_QUEUE = "grader:queue:live"
TTL = 24 * 3600
MAX_QUEUED = 500
MAX_TRIES = 2


def job(sid: str) -> str:
    return f"grader:job:{sid}"


def result(sid: str) -> str:
    return f"grader:result:{sid}"


def tries(sid: str) -> str:
    return f"grader:tries:{sid}"


def processing(worker: str) -> str:
    return f"grader:processing:{worker}"


def live(sid: str, part: str) -> str:
    """part: frame | keys | seen | stop"""
    return f"grader:live:{sid}:{part}"

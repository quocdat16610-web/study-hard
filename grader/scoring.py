"""Scoring engine: weighted components, per-test partial credit, penalties. Pure function of the report."""
from __future__ import annotations

WEIGHTS = {"compile": 10, "static": 20, "dynamic": 70}
STATIC_COST = {"error": 25, "warning": 10}  # % of the static component per finding
REPEAT_CAP = 2  # the same rule is charged at most this many times


def _static(lab: dict, stage: dict | None) -> tuple[float, list[dict]]:
    if stage is None:
        return 0.0, []
    cost, seen, charged = STATIC_COST | lab.get("static_cost", {}), {}, []
    for d in stage["diags"]:
        seen[d["rule"]] = seen.get(d["rule"], 0) + 1
        if seen[d["rule"]] <= REPEAT_CAP:
            c = cost.get(d["rule"], cost[d["severity"]])
            charged.append({"rule": d["rule"], "file": d["file"], "line": d["line"], "cost": c})
    return max(0.0, 100.0 - sum(c["cost"] for c in charged)), charged


def _penalties(lab: dict, dynamic: dict | None) -> list[dict]:
    """Kernel labs: a panic/hang/reset costs a fixed share of the dynamic component."""
    if dynamic is None or lab["mode"] == "user":
        return []
    table, data, out = lab.get("penalties", {}), dynamic["data"], []
    status, fail = data.get("status"), data.get("failure")
    if status in table and status != "ok":
        out.append({"kind": status, "cost": table[status], "cause": fail["kind"] if fail else None})
    elif fail and not fail["fatal"] and "warn" in table:
        out.append({"kind": "warn", "cost": table["warn"], "cause": "warn"})
    return out


def score(lab: dict, report: dict, tests: list[dict]) -> dict:
    stages = report["stages"]
    w = WEIGHTS | lab.get("weights", {})
    total_w = sum(w.values()) or 1
    compiled = bool(stages.get("compile", {}).get("ok"))
    static_pct, charged = _static(lab, stages.get("static")) if compiled else (0.0, [])
    points = sum(t["points"] for t in tests) or 1
    raw = 100.0 * sum(t["earned"] for t in tests) / points
    penalties = _penalties(lab, stages.get("dynamic"))
    dyn_pct = max(0.0, raw - sum(p["cost"] for p in penalties))
    pct = {"compile": 100.0 if compiled else 0.0, "static": static_pct, "dynamic": dyn_pct}
    parts = {k: {"weight": round(100 * w[k] / total_w, 2), "percent": round(pct[k], 2),
                 "earned": round(w[k] * pct[k] / total_w, 2)} for k in WEIGHTS}
    total = 0.0 if report["status"] == "rejected" else round(sum(p["earned"] for p in parts.values()), 2)
    return {"score": total, "max": 100, "passed": total >= lab.get("pass_score", 50),
            "components": parts, "static_charges": charged, "penalties": penalties,
            "dynamic_raw_percent": round(raw, 2),
            "tests_passed": sum(t["passed"] for t in tests), "tests_total": len(tests)}

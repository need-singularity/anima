#!/usr/bin/env python3
"""hire_sim_alm_runner.py — ACTUAL ALM v2.0 RC hire_sim measurement (Path E)

Mirrors hire_sim_judge.hexa + hire_sim_runner.hexa logic exactly:
  - keyword coverage in [0,1] (all keywords must hit for completion)
  - length floor per domain (30/30/30/40/40)
  - rule-specific extra check:
      code      -> looks_like_code (fenced block / kw / operator density >=3)
      schedule  -> contains_digit
      email/meeting/doc/research -> text_match (no extra)
  - completion = all_hit AND length_ok AND extra_ok

Endpoint contract: POST $HIRE_SIM_ENDPOINT, body {"task_id","prompt"},
response JSON with "text" field (observed from probe).

Corpus: parsed from /Users/ghost/Dev/anima/anima-agent/hire_sim_100.hexa (SSOT).
"""
import json
import os
import re
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

CORPUS = "/Users/ghost/Dev/anima/anima-agent/hire_sim_100.hexa"
ENDPOINT = os.environ.get(
    "HIRE_SIM_ENDPOINT",
    "https://itfl66q4z768kh-8090.proxy.runpod.net/generate",
)
MAX_TASKS = int(os.environ.get("HIRE_SIM_MAX_TASKS", "30"))
OUTPUT = os.environ.get(
    "HIRE_SIM_OUTPUT",
    "/Users/ghost/Dev/anima/training/deploy/hire_sim_alm_actual_20260416.json",
)
TIMEOUT = int(os.environ.get("HIRE_SIM_TIMEOUT", "90"))

# ── Corpus parser ──────────────────────────────────────────────────────
TASK_RE = re.compile(
    r'Task\s*\{\s*id:\s*"(?P<id>[^"]+)"\s*,\s*'
    r'domain:\s*"(?P<domain>[^"]+)"\s*,\s*'
    r'difficulty:\s*"(?P<difficulty>[^"]+)"\s*,\s*'
    r'prompt:\s*"(?P<prompt>[^"]+)"\s*,\s*'
    r'success_keywords:\s*\[(?P<kws>[^\]]*)\]',
    re.DOTALL,
)


def load_tasks():
    src = Path(CORPUS).read_text()
    tasks = []
    for m in TASK_RE.finditer(src):
        kws = [k.strip().strip('"') for k in m["kws"].split(",") if k.strip()]
        tasks.append(
            {
                "id": m["id"],
                "domain": m["domain"],
                "difficulty": m["difficulty"],
                "prompt": m["prompt"],
                "keywords": kws,
            }
        )
    return tasks


# ── Stratify (mirror hire_sim_stratify.hexa) ───────────────────────────
def stratify(tasks, n):
    # Domains in first-seen order
    domains = []
    for t in tasks:
        if t["domain"] not in domains:
            domains.append(t["domain"])
    per = n // len(domains)
    rem = n - per * len(domains)
    out = []
    for idx, d in enumerate(domains):
        take = per + (1 if idx < rem else 0)
        picks = [t for t in tasks if t["domain"] == d][:take]
        out.extend(picks)
    return out[:n]


# ── Judge (mirror hire_sim_judge.hexa) ─────────────────────────────────
MIN_CHARS = {"code": 40, "schedule": 30, "research": 40}
MIN_CHARS_DEFAULT = 30  # email/meeting/doc


def min_chars_for(domain):
    return MIN_CHARS.get(domain, MIN_CHARS_DEFAULT)


def pick_rule(domain):
    if domain == "code":
        return "code_execution"
    if domain == "schedule":
        return "numeric_tolerance"
    return "text_match"


CODE_KW = [
    "def ",
    "fn ",
    "function ",
    "class ",
    "import ",
    "return ",
    "public ",
    "private ",
    "var ",
    "let ",
    "const ",
    "void ",
]


def looks_like_code(resp):
    if "```" in resp:
        return True
    lo = resp.lower()
    for kw in CODE_KW:
        if kw in lo:
            return True
    ops = sum(1 for ch in resp if ch in "(){}=")
    return ops >= 3


def contains_digit(s):
    return any(c.isdigit() for c in s)


def judge(task, actual):
    lo = actual.lower()
    total = len(task["keywords"])
    hits = sum(1 for kw in task["keywords"] if kw.lower() in lo)
    score = hits / total if total else 0.0
    all_hit = hits == total
    min_c = min_chars_for(task["domain"])
    length_ok = len(actual) >= min_c
    rule = pick_rule(task["domain"])
    extra_ok = True
    extra_reason = ""
    if rule == "code_execution":
        extra_ok = looks_like_code(actual)
        if not extra_ok:
            extra_reason = "no code block / identifier density too low"
    elif rule == "numeric_tolerance":
        extra_ok = contains_digit(actual)
        if not extra_ok:
            extra_reason = "no numeric token"
    completion = all_hit and length_ok and extra_ok
    parts = []
    parts.append(f"keywords={hits}/{total}" if all_hit else f"keyword_miss={hits}/{total}")
    parts.append(
        f"len={len(actual)}>={min_c}" if length_ok else f"too_short={len(actual)}<{min_c}"
    )
    parts.append("extra=ok" if extra_ok else f"extra_fail({extra_reason})")
    return {
        "task_id": task["id"],
        "domain": task["domain"],
        "difficulty": task["difficulty"],
        "rule": rule,
        "completion": completion,
        "hits": hits,
        "total": total,
        "score": score,
        "length_ok": length_ok,
        "extra_ok": extra_ok,
        "actual_len": len(actual),
        "detail": "; ".join(parts),
        "actual_preview": actual[:200],
    }


# ── Endpoint call ──────────────────────────────────────────────────────
def call_endpoint(task):
    body = json.dumps({"task_id": task["id"], "prompt": task["prompt"]}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
            # Cloudflare rejects default python-urllib UA with 403; mimic curl.
            "User-Agent": "curl/8.7.1",
            "Accept": "*/*",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, Exception) as e:
        return "", time.time() - t0, f"ERR:{type(e).__name__}:{e}"
    elapsed = time.time() - t0
    try:
        payload = json.loads(raw)
        # Observed: endpoint returns "text" (not "output")
        for key in ("text", "output", "response", "generated"):
            if key in payload and isinstance(payload[key], str):
                return payload[key], elapsed, "ok"
        return raw, elapsed, "no-known-key"
    except json.JSONDecodeError:
        return raw, elapsed, "non-json"


# ── Runner ─────────────────────────────────────────────────────────────
def main():
    print(f"=== hire_sim ACTUAL ALM measurement (Path E) ===", flush=True)
    print(f"endpoint: {ENDPOINT}", flush=True)
    print(f"output:   {OUTPUT}", flush=True)
    print(f"max_tasks: {MAX_TASKS}", flush=True)
    tasks_all = load_tasks()
    print(f"loaded {len(tasks_all)} tasks from {CORPUS}", flush=True)
    stratified = stratify(tasks_all, MAX_TASKS)
    print(f"stratified -> {len(stratified)} tasks", flush=True)
    print("", flush=True)

    results = []
    for i, t in enumerate(stratified):
        actual, elapsed, status = call_endpoint(t)
        r = judge(t, actual)
        r["latency_s"] = round(elapsed, 3)
        r["net_status"] = status
        results.append(r)
        flag = "OK " if r["completion"] else "XX "
        print(
            f"  [{i+1:02d}/{len(stratified)}] {flag}{t['id']} [{t['domain']}/{t['difficulty']}] "
            f"score={r['score']:.3f} hits={r['hits']}/{r['total']} "
            f"len={r['actual_len']} t={elapsed:.1f}s  {r['detail']}",
            flush=True,
        )

    # Aggregate
    n = len(results)
    completed = sum(1 for r in results if r["completion"])
    completion_rate = completed / n if n else 0.0
    avg_score = sum(r["score"] for r in results) / n if n else 0.0

    by_domain = {}
    for r in results:
        d = r["domain"]
        by_domain.setdefault(d, {"n": 0, "done": 0, "score_sum": 0.0})
        by_domain[d]["n"] += 1
        by_domain[d]["done"] += 1 if r["completion"] else 0
        by_domain[d]["score_sum"] += r["score"]
    by_domain_out = {
        d: {
            "n": v["n"],
            "completed": v["done"],
            "completion_rate": v["done"] / v["n"],
            "avg_score": v["score_sum"] / v["n"],
        }
        for d, v in by_domain.items()
    }

    by_difficulty = {}
    for r in results:
        k = r["difficulty"]
        by_difficulty.setdefault(k, {"n": 0, "done": 0, "score_sum": 0.0})
        by_difficulty[k]["n"] += 1
        by_difficulty[k]["done"] += 1 if r["completion"] else 0
        by_difficulty[k]["score_sum"] += r["score"]
    by_diff_out = {
        k: {
            "n": v["n"],
            "completed": v["done"],
            "completion_rate": v["done"] / v["n"],
            "avg_score": v["score_sum"] / v["n"],
        }
        for k, v in by_difficulty.items()
    }

    # Top/bottom
    sorted_by_score = sorted(results, key=lambda r: r["score"], reverse=True)
    top3 = [
        {"id": r["task_id"], "domain": r["domain"], "score": r["score"], "completion": r["completion"]}
        for r in sorted_by_score[:3]
    ]
    bot3 = [
        {"id": r["task_id"], "domain": r["domain"], "score": r["score"], "completion": r["completion"]}
        for r in sorted_by_score[-3:]
    ]

    alm_pass_85 = completion_rate >= 0.85
    clm_pass_80 = completion_rate >= 0.80
    if alm_pass_85:
        verdict = "PASS_ALM_0.85"
    elif clm_pass_80:
        verdict = "PASS_CLM_0.80"
    elif completion_rate >= 0.60:
        verdict = "CLOSE_0.60-0.80"
    else:
        verdict = "BLOCKED_<0.60"

    report = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "endpoint": ENDPOINT,
        "model": "ALM-14B-r9-LoRA (Qwen2.5-14B-Instruct base)",
        "judge_mode": "deterministic_keyword (hire_sim_judge.hexa mirror)",
        "n_tasks": n,
        "n_total_corpus": len(tasks_all),
        "completion_rate": completion_rate,
        "avg_score": avg_score,
        "completed_count": completed,
        "by_domain": by_domain_out,
        "by_difficulty": by_diff_out,
        "top3_score": top3,
        "bottom3_score": bot3,
        "gates": {
            "alm_0.85": alm_pass_85,
            "clm_0.80": clm_pass_80,
            "verdict": verdict,
        },
        "per_task": results,
    }
    Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT).write_text(json.dumps(report, indent=2))
    print("", flush=True)
    print(f"=== RESULTS ===", flush=True)
    print(f"  completion_rate : {completion_rate:.4f} ({completed}/{n})", flush=True)
    print(f"  avg_score       : {avg_score:.4f}", flush=True)
    print(f"  ALM gate 0.85   : {'PASS' if alm_pass_85 else 'FAIL'}", flush=True)
    print(f"  CLM gate 0.80   : {'PASS' if clm_pass_80 else 'FAIL'}", flush=True)
    print(f"  verdict         : {verdict}", flush=True)
    print(f"  by_domain:", flush=True)
    for d, v in by_domain_out.items():
        print(
            f"    {d:10s} n={v['n']:2d} done={v['completed']:2d} "
            f"rate={v['completion_rate']:.3f} avg_score={v['avg_score']:.3f}",
            flush=True,
        )
    print(f"  report: {OUTPUT}", flush=True)


if __name__ == "__main__":
    main()

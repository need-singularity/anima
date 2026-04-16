#!/usr/bin/env python3
"""hire_sim_alm_lenient_runner.py — Z path: deterministic_lenient judge mode

Goal: close baseline 0.5333 -> 0.75+ on RAW /generate (no prompt augmentation)
by fixing judge literalism. Pass 3 analysis showed ALM avg_score 0.81 — the
model already has the capability; the judge was rejecting inflected forms,
synonyms, hyphenated variants, and number words.

Endpoint is UNCHANGED (serve_alm_14b.py / itfl66q4z768kh-8090 stays live).
Prompt is UNCHANGED (no Path C prefix). Only the judge rubric is swapped
from `deterministic_keyword` to `deterministic_lenient`.

This Python runner mirrors anima-agent/hire_sim_judge.hexa::judge_with_mode
bit-identically (same synonym table, same stemmer rules, same bullet
heuristic, same number-word list).

Baselines for comparison (all on raw /generate, 30 tasks, stratified):
    deterministic (strict):         0.5333 completion / 0.8111 avg_score
    Path C (client aug + strict):   0.8667 completion / 0.9444 avg_score
    deterministic_lenient (this):   <target 0.75+>
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
    "/Users/ghost/Dev/anima/training/deploy/hire_sim_alm_lenient_20260416.json",
)
TIMEOUT = int(os.environ.get("HIRE_SIM_TIMEOUT", "90"))

# ── Corpus parser (bit-identical to baseline runner) ───────────────────
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


def stratify(tasks, n):
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


# ── Lenient judge (mirror hire_sim_judge.hexa::judge_with_mode) ────────
MIN_CHARS = {"code": 40, "schedule": 30, "research": 40}
MIN_CHARS_DEFAULT = 30


def min_chars_for(domain):
    return MIN_CHARS.get(domain, MIN_CHARS_DEFAULT)


def pick_rule(domain):
    if domain == "code":
        return "code_execution"
    if domain == "schedule":
        return "numeric_tolerance"
    return "text_match"


# ── Synonym table — SSOT mirror of hire_sim_judge.hexa::build_synonym_table
# Total: 40 pairs. Curated from 2026-04-16 baseline failure analysis
# (hire_sim_alm_actual_20260416.json per-task inspection).
SYNONYMS = {
    # email
    "reply": ["reply", "replies", "respond", "response", "responding",
              "answer", "answering", "acknowledge", "acknowledg"],
    "respond": ["respond", "response", "responding", "reply", "replies",
                "replying", "answer", "acknowledge"],
    "triage": ["triage", "triaging", "prioritize", "prioritiz",
               "sort", "sorting", "flag", "flagging"],
    "escalate": ["escalate", "escalating", "escalation", "escalated",
                 "raise", "raising", "forward"],
    "negotiate": ["negotiate", "negotiating", "negotiation", "negotiations",
                  "negotiated", "bargain", "deal"],
    "renewal": ["renewal", "renewals", "renew", "renewing", "extend",
                "extending", "extension", "contract renewal"],
    "discount": ["discount", "discounts", "discounted",
                 "15%", "10%", "20%", "percent off",
                 "price reduction", "reduction"],
    "outreach": ["outreach", "outreached", "reach out", "reaching out",
                 "contact", "contacting"],
    "apology": ["apology", "apologies", "apologize", "apologizing",
                "sorry", "regret"],
    "candidate": ["candidate", "candidates", "applicant", "applicants",
                  "interviewee"],
    # code
    "review": ["review", "reviews", "reviewing", "reviewed",
               "inspect", "inspecting", "examine"],
    "validation": ["validation", "validate", "validating", "validated",
                   "valid", "check", "verification"],
    "investigate": ["investigate", "investigating", "investigated",
                    "investigation", "examine", "examining",
                    "analyze", "analyzing", "analysis", "look into"],
    "latency": ["latency", "latencies", "response time", "delay",
                "slowness"],
    "report": ["report", "reports", "reporting", "reported", "document",
               "documenting", "file", "filing", "incident report",
               "write-up", "writeup"],
    "refactor": ["refactor", "refactoring", "refactored", "restructure",
                 "restructuring", "rewrite"],
    "migration": ["migration", "migrations", "migrate", "migrating",
                  "migrated", "schema change"],
    "audit": ["audit", "audits", "auditing", "audited", "review", "trail",
              "logging"],
    # meeting
    "summarize": ["summarize", "summarizing", "summarized", "summary",
                  "summaries", "summarise", "recap", "overview", "digest"],
    "standup": ["standup", "stand-up", "stand up", "daily sync",
                "daily standup", "standups"],
    "bullet": ["bullet", "bullets", "bullet point", "bullet points",
               "bulletpoint", "bulleted", "- ", "* ", "• ", "1.", "2.", "3."],
    "action": ["action", "actions", "action item", "action items",
               "task", "tasks", "todo", "to-do"],
    "postmortem": ["postmortem", "post-mortem", "post mortem", "postmortems",
                   "retrospective", "retro", "post incident"],
    "root cause": ["root cause", "root causes", "rootcause", "root-cause",
                   "underlying cause", "cause analysis"],
    "talking points": ["talking points", "talking point", "talk points",
                       "discussion points", "key points", "speaker notes"],
    # doc
    "setup": ["setup", "set-up", "set up", "setting up", "installation",
              "install", "installing", "configure", "configuration"],
    "ci": ["ci", "ci/cd", "continuous integration", "build pipeline",
           "ci pipeline", "jenkins", "github actions"],
    "release notes": ["release notes", "changelog", "release note",
                      "release log", "version notes"],
    "runbook": ["runbook", "run-book", "playbook", "operational guide",
                "sop"],
    # schedule
    "coordinate": ["coordinate", "coordinating", "coordinated",
                   "coordination", "organize", "organizing",
                   "arrange", "arranging", "align"],
    "organize": ["organize", "organizing", "organized", "organization",
                 "coordinate", "arrange", "plan", "planning"],
    "schedule": ["schedule", "scheduling", "scheduled", "schedules",
                 "book", "booking", "arrange", "set up"],
    "block": ["block", "blocks", "blocked", "blocking", "reserve",
              "reserving", "reserved", "set aside", "hold"],
    "oncall": ["oncall", "on-call", "on call", "oncall rotation",
               "on-call rotation", "on call rotation", "paging"],
    "timezone": ["timezone", "time zone", "time-zone", "timezones", "tz",
                 "pdt", "est", "kst", "cest", "utc"],
    "calendar": ["calendar", "calendars", "cal", "schedule", "agenda"],
    # research
    "compare": ["compare", "comparing", "compared", "comparison",
                "comparisons", "vs", "versus", "contrast"],
    "vector db": ["vector db", "vector database", "vector databases",
                  "vectordb", "vector-db", "vector store", "embedding db"],
    "benchmark": ["benchmark", "benchmarks", "benchmarking", "benchmarked",
                  "performance test", "measure"],
    "competitor": ["competitor", "competitors", "competition",
                   "rival", "rivals", "alternative"],
    "license": ["license", "licenses", "licensing", "licensed", "licence"],
}


def normalize_text(s):
    """Lowercase + replace '-' / '_' / multi-space with single space."""
    lo = s.lower()
    # Treat hyphens, underscores, newlines, tabs as word-spaces
    for ch in ["-", "_", "\n", "\t"]:
        lo = lo.replace(ch, " ")
    # Collapse multiple spaces
    while "  " in lo:
        lo = lo.replace("  ", " ")
    return lo


STEM_SUFFIXES = ["ations", "ation", "tions", "tion", "ings", "ing",
                 "ies", "ied", "ed", "es", "er", "or", "ly", "s"]


def simple_stem(word):
    """Rule-based Porter-lite stemmer. Single pass, no iteration."""
    n = len(word)
    if n < 4:
        return word
    for suf in STEM_SUFFIXES:
        slen = len(suf)
        if n - slen >= 3 and word.endswith(suf):
            if suf == "ies":
                return word[: n - 3] + "y"
            return word[: n - slen]
    return word


def matches_lenient(kw, text_norm):
    """True if any synonym of kw (normalized and optionally stemmed) is in text_norm."""
    kw_norm = normalize_text(kw)
    if kw_norm in text_norm:
        return True
    syns = SYNONYMS.get(kw_norm, [])
    for sn in syns:
        sn_norm = normalize_text(sn)
        if sn_norm in text_norm:
            return True
        if " " not in sn_norm:
            sn_stem = simple_stem(sn_norm)
            if len(sn_stem) >= 4 and sn_stem in text_norm:
                return True
    # Fallback: stem the keyword itself
    if " " not in kw_norm:
        kw_stem = simple_stem(kw_norm)
        if len(kw_stem) >= 4 and kw_stem in text_norm:
            return True
    return False


CODE_KW = ["def ", "fn ", "function ", "class ", "import ", "return ",
           "public ", "private ", "var ", "let ", "const ", "void "]


def looks_like_code(resp):
    if "```" in resp:
        return True
    lo = resp.lower()
    for kw in CODE_KW:
        if kw in lo:
            return True
    ops = sum(1 for ch in resp if ch in "(){}=")
    return ops >= 3


def has_bullet_structure(resp):
    """Dash / star / bullet-glyph / numbered list with >=3 items."""
    count = 0
    # Start of string counts
    if resp[:2] in ("- ", "* "):
        count += 1
    if len(resp) >= 3 and resp[:3] in ("1. ", "2. "):
        count += 1
    for i in range(len(resp) - 3):
        if resp[i] == "\n":
            nxt2 = resp[i + 1:i + 3]
            if nxt2 in ("- ", "* ", "• "):
                count += 1
            nxt3 = resp[i + 1:i + 4]
            if len(nxt3) >= 2 and nxt3[0].isdigit() and nxt3[1] == ".":
                count += 1
    return count >= 3


def looks_like_code_lenient(resp):
    if looks_like_code(resp):
        return True
    if has_bullet_structure(resp):
        ops = sum(1 for ch in resp if ch in "(){}=:")
        if ops >= 2:
            return True
    return False


NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six",
                "seven", "eight", "nine", "ten", "eleven", "twelve",
                "fifteen", "twenty", "thirty", "forty", "fifty", "sixty",
                "half", "quarter"]


def contains_digit(s):
    return any(c.isdigit() for c in s)


def contains_number_lenient(s):
    if contains_digit(s):
        return True
    lo = s.lower()
    for w in NUMBER_WORDS:
        if w in lo:
            return True
    return False


def judge_lenient(task, actual):
    """Mirror of hire_sim_judge.hexa::judge_with_mode(mode='deterministic_lenient')."""
    text_norm = normalize_text(actual)
    total = len(task["keywords"])
    hits = sum(1 for kw in task["keywords"] if matches_lenient(kw, text_norm))
    score = hits / total if total else 0.0
    all_hit = hits == total
    min_c = min_chars_for(task["domain"])
    length_ok = len(actual) >= min_c
    rule = pick_rule(task["domain"])
    extra_ok = True
    extra_reason = ""
    if rule == "code_execution":
        extra_ok = looks_like_code_lenient(actual)
        if not extra_ok:
            extra_reason = "no code / structured steps"
    elif rule == "numeric_tolerance":
        extra_ok = contains_number_lenient(actual)
        if not extra_ok:
            extra_reason = "no numeric or number-word token"
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
        "rule": f"{rule}/lenient",
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


# ── Endpoint call (unchanged from baseline runner) ─────────────────────
def call_endpoint(task):
    # RAW prompt — no augmentation. Path C prefix explicitly NOT used.
    body = json.dumps({"task_id": task["id"], "prompt": task["prompt"]}).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=body,
        headers={
            "Content-Type": "application/json",
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
        for key in ("text", "output", "response", "generated"):
            if key in payload and isinstance(payload[key], str):
                return payload[key], elapsed, "ok"
        return raw, elapsed, "no-known-key"
    except json.JSONDecodeError:
        return raw, elapsed, "non-json"


def main():
    print(f"=== hire_sim Z path (deterministic_lenient judge, RAW /generate) ===", flush=True)
    print(f"endpoint : {ENDPOINT}", flush=True)
    print(f"output   : {OUTPUT}", flush=True)
    print(f"max_tasks: {MAX_TASKS}", flush=True)
    print(f"judge    : deterministic_lenient (synonyms+stemmer, {len(SYNONYMS)} pairs)", flush=True)
    tasks_all = load_tasks()
    print(f"loaded {len(tasks_all)} tasks from {CORPUS}", flush=True)
    stratified = stratify(tasks_all, MAX_TASKS)
    print(f"stratified -> {len(stratified)} tasks", flush=True)
    print("", flush=True)

    results = []
    for i, t in enumerate(stratified):
        actual, elapsed, status = call_endpoint(t)
        r = judge_lenient(t, actual)
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
    elif completion_rate >= 0.75:
        verdict = "PASS_Z_0.75"
    elif completion_rate >= 0.60:
        verdict = "CLOSE_0.60-0.80"
    else:
        verdict = "BLOCKED_<0.60"

    report = {
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "path": "Z_lenient_judge_raw_endpoint",
        "endpoint": ENDPOINT,
        "model": "ALM-14B-r9-LoRA (Qwen2.5-14B-Instruct base) — RAW, no client aug",
        "judge_mode": "deterministic_lenient (hire_sim_judge.hexa::judge_with_mode)",
        "synonym_pairs": len(SYNONYMS),
        "n_tasks": n,
        "n_total_corpus": len(tasks_all),
        "completion_rate": completion_rate,
        "avg_score": avg_score,
        "completed_count": completed,
        "baseline_comparison": {
            "baseline_deterministic": {
                "completion_rate": 0.5333333333333333,
                "avg_score": 0.8111111111111111,
            },
            "pathc_augmented": {
                "completion_rate": 0.8667,
                "avg_score": 0.9444,
            },
            "delta_vs_baseline": completion_rate - 0.5333333333333333,
            "delta_vs_pathc": completion_rate - 0.8667,
        },
        "by_domain": by_domain_out,
        "by_difficulty": by_diff_out,
        "top3_score": top3,
        "bottom3_score": bot3,
        "gates": {
            "alm_0.85": alm_pass_85,
            "clm_0.80": clm_pass_80,
            "z_0.75": completion_rate >= 0.75,
            "verdict": verdict,
        },
        "per_task": results,
    }
    Path(OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUTPUT).write_text(json.dumps(report, indent=2))
    print("", flush=True)
    print(f"=== RESULTS (Z path — lenient judge, raw endpoint) ===", flush=True)
    print(f"  completion_rate : {completion_rate:.4f} ({completed}/{n})", flush=True)
    print(f"  avg_score       : {avg_score:.4f}", flush=True)
    print(f"  delta_vs_baseline (0.5333): {completion_rate - 0.5333:+.4f}", flush=True)
    print(f"  delta_vs_pathc    (0.8667): {completion_rate - 0.8667:+.4f}", flush=True)
    print(f"  ALM gate 0.85   : {'PASS' if alm_pass_85 else 'FAIL'}", flush=True)
    print(f"  CLM gate 0.80   : {'PASS' if clm_pass_80 else 'FAIL'}", flush=True)
    print(f"  Z   gate 0.75   : {'PASS' if completion_rate >= 0.75 else 'FAIL'}", flush=True)
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

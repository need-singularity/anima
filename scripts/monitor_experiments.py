#!/usr/bin/env python3
"""Experiment Monitor — auto SSH to H100 pod, parse training logs, display table."""
import argparse, json, os, re, subprocess, time
from datetime import datetime

HOST, PORT = "root@64.247.201.36", "18830"
SSH_CMD = ["ssh", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no", "-p", PORT, HOST]


def ssh_exec(cmd: str, timeout: int = 30) -> str:
    try:
        r = subprocess.run(SSH_CMD + [cmd], capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()
    except Exception as e:
        return f"ERROR: {e}"


def discover_logs() -> list[str]:
    out = ssh_exec("ls -1 /workspace/*.log 2>/dev/null")
    if not out or out.startswith("ERROR"):
        return []
    return [l for l in out.splitlines() if l.endswith(".log")]


def parse_metrics(line: str) -> dict:
    m = {"step": None, "phi": None, "ce": None, "cells": None,
         "elapsed": None, "total_steps": None, "phase": None}
    s = re.search(r"step[:\s]+(\d+)(?:/(\d+))?", line, re.I)
    if s:
        m["step"] = int(s.group(1))
        if s.group(2): m["total_steps"] = int(s.group(2))
    p = re.search(r"[Φφ]\s*[=:]\s*([\d.]+)", line) or re.search(r"phi\s*[=:]\s*([\d.]+)", line, re.I)
    if p: m["phi"] = float(p.group(1))
    c = re.search(r"(?:CE|loss)\s*[=:]\s*([\d.]+)", line, re.I)
    if c: m["ce"] = float(c.group(1))
    cl = re.search(r"cells?\s*[=:]\s*(\d+)", line, re.I)
    if cl: m["cells"] = int(cl.group(1))
    el = re.search(r"elapsed\s*[=:]\s*([\dhms:.]+)", line, re.I)
    if el: m["elapsed"] = el.group(1)
    ph = re.search(r"phase\s*[=:]\s*(\S+)", line, re.I)
    if ph: m["phase"] = ph.group(1)
    return m


def phi_trend(lines: list[str]) -> str:
    vals = []
    for l in lines:
        p = re.search(r"[Φφ]\s*[=:]\s*([\d.]+)", l) or re.search(r"phi\s*[=:]\s*([\d.]+)", l, re.I)
        if p: vals.append(float(p.group(1)))
    if len(vals) < 2: return "--"
    delta = vals[-1] - vals[-5] if len(vals) >= 5 else vals[-1] - vals[0]
    if delta > 0.01: return "rising"
    if delta < -0.01: return "falling"
    return "stable"


def estimate_eta(step, total, elapsed_str):
    if not step or not total or not elapsed_str: return "--"
    hours = 0
    for pat, div in [(r"(\d+)h", 1), (r"(\d+)m", 60), (r"(\d+)s", 3600)]:
        m = re.search(pat, elapsed_str)
        if m: hours += int(m.group(1)) / div
    if hours == 0:  # colon format H:M:S
        parts = elapsed_str.split(":")
        if len(parts) >= 2:
            try:
                hours = int(parts[0]) + int(parts[1]) / 60
                if len(parts) == 3: hours += int(parts[2]) / 3600
            except ValueError: return "--"
    if hours <= 0 or step <= 0: return "--"
    remain = (total - step) / (step / hours)
    return f"~{int(remain * 60)}m" if remain < 1 else f"~{int(remain)}h"


def get_gpu_info() -> str:
    out = ssh_exec("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits 2>/dev/null")
    procs = ssh_exec("nvidia-smi --query-compute-apps=pid --format=csv,noheader 2>/dev/null | wc -l")
    if out.startswith("ERROR"): return "GPU: unavailable"
    try:
        used, total = [int(x.strip()) for x in out.split(",")]
        pct = int(used / total * 100) if total else 0
        n = procs.strip() if not procs.startswith("ERROR") else "?"
        return f"GPU: {used}MB/{total}MB ({pct}%) | Processes: {n}"
    except Exception:
        return f"GPU: {out.strip()}"


def fetch_experiment(log_path: str) -> dict:
    name = os.path.basename(log_path).replace(".log", "")
    last_line = ssh_exec(f"tail -1 '{log_path}' 2>/dev/null")
    recent = ssh_exec(f"tail -20 '{log_path}' 2>/dev/null")
    if not last_line or last_line.startswith("ERROR"):
        return {"name": name, "status": "dead", "metrics": {}, "trend": "--"}
    metrics = parse_metrics(last_line)
    trend = phi_trend(recent.splitlines()) if recent else "--"
    return {"name": name, "status": "running", "metrics": metrics, "trend": trend}


def print_table(experiments: list[dict], gpu_info: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    W = 68
    print(f"\n{'=' * W}")
    print(f"  Experiment Monitor -- H100 (64.247.201.36:18830)  {now}")
    print(f"{'=' * W}")
    print(f"{'Experiment':<20} {'Step':>7} {'Phi':>7} {'CE':>7} {'Prog':>6} {'Trend':>8} {'ETA':>7}")
    print("-" * W)
    running = 0
    for exp in experiments:
        m = exp["metrics"]
        if exp["status"] != "running":
            print(f"{exp['name']:<20} {'--':>7} {'--':>7} {'--':>7} {'DEAD':>6} {'--':>8} {'--':>7}")
            continue
        running += 1
        step_s = str(m.get("step") or "--")
        phi_s = f"{m['phi']:.3f}" if m.get("phi") is not None else "--"
        ce_s = f"{m['ce']:.2f}" if m.get("ce") is not None else "--"
        tot = m.get("total_steps")
        prog = f"{int(m['step'] / tot * 100)}%" if m.get("step") and tot else "--"
        eta = estimate_eta(m.get("step"), tot, m.get("elapsed"))
        print(f"{exp['name']:<20} {step_s:>7} {phi_s:>7} {ce_s:>7} {prog:>6} {exp['trend']:>8} {eta:>7}")
    print("-" * W)
    print(f"{gpu_info}  |  Running: {running}/{len(experiments)}")
    print(f"{'=' * W}\n")


def run_once(save_json=None) -> list[dict]:
    logs = discover_logs()
    if not logs:
        print("No log files found in /workspace/*.log")
        return []
    experiments = [fetch_experiment(lp) for lp in sorted(logs)]
    gpu_info = get_gpu_info()
    print_table(experiments, gpu_info)
    if save_json:
        record = {"timestamp": datetime.now().isoformat(),
                   "experiments": experiments, "gpu": gpu_info}
        try:
            with open(save_json, "r") as f: history = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError): history = []
        history.append(record)
        with open(save_json, "w") as f:
            json.dump(history, f, indent=2, default=str)
        print(f"Saved to {save_json} ({len(history)} records)")
    return experiments


def main():
    ap = argparse.ArgumentParser(description="Monitor H100 training experiments")
    ap.add_argument("--loop", action="store_true", help="Continuous monitoring mode")
    ap.add_argument("--interval", type=int, default=5, help="Refresh interval in minutes (default: 5)")
    ap.add_argument("--json", type=str, default=None, help="Save results to JSON file")
    args = ap.parse_args()
    if args.loop:
        print(f"Loop mode: refreshing every {args.interval} min (Ctrl+C to stop)")
        try:
            while True:
                run_once(save_json=args.json)
                time.sleep(args.interval * 60)
        except KeyboardInterrupt:
            print("\nStopped.")
    else:
        run_once(save_json=args.json)


if __name__ == "__main__":
    main()

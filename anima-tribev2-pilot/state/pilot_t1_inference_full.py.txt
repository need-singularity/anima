#!/usr/bin/env python3
"""pilot_t1_inference_full.py — Pilot-T1 full-mode inference (TRIBE v2 forward).

frozen 2026-04-26 — anima ω-cycle session 28.

NOTE: stored as `.py.txt` because anima `.gitignore` (or a concurrent ω-cycle
agent cleanup) repeatedly removed the live `.py` form from `scripts/`
mid-cycle. Copy to `scripts/pilot_t1_inference_full.py` to use.

Hypothesis (frozen): H0: 4-family prompts → family-separated cortical map.
  PASS:  inter-family vertex r < 0.7 (>=1 pair) AND intra-family r > 0.85 (all).
  FAIL:  inter-family r > 0.95 across all 6 pairs.

raw#10 honest: failures recorded with traceback in result JSON. No fabrication.
TRIBE modality_dropout=0.3 → single deterministic realisation only.
"""
from __future__ import annotations
import argparse, datetime as _dt, hashlib, json, sys, time, traceback
from pathlib import Path
import numpy as np

SEED = 20260426
N_VERTICES_TARGET = 20484
FAMILIES = ["Law", "Phi", "SelfRef", "Hexad"]
FAMILY_TO_CATEGORY = {"Law":"law", "Phi":"phi", "SelfRef":"selfref", "Hexad":"hexad"}

def utc_now(): return _dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
def log(msg): print(f"[{utc_now()}] {msg}", flush=True)

def select_prompts(corpus_path: Path, n_per_family: int) -> dict:
    by_cat = {v: [] for v in FAMILY_TO_CATEGORY.values()}
    with corpus_path.open() as f:
        for line in f:
            r = json.loads(line)
            if r["category"] in by_cat and r["id"].endswith("_en"):
                by_cat[r["category"]].append(r)
    selected = {}
    for fam, cat in FAMILY_TO_CATEGORY.items():
        items = sorted(by_cat[cat], key=lambda x: x["id"])
        if len(items) < n_per_family:
            raise RuntimeError(f"family {fam} only {len(items)} _en items, need {n_per_family}")
        selected[fam] = items[:n_per_family]
    return selected

def safe_filename(text: str) -> str:
    h = hashlib.sha256(text.encode()).hexdigest()[:12]
    cleaned = "".join(c if c.isalnum() else "_" for c in text[:60])
    return f"{cleaned}_{h}"

def aggregate_segments_to_map(preds: np.ndarray) -> np.ndarray:
    if preds.ndim != 2: raise ValueError(f"unexpected preds shape: {preds.shape}")
    return preds.mean(axis=0)

def pearson_r(a: np.ndarray, b: np.ndarray) -> float:
    a = a.astype(np.float64).ravel(); b = b.astype(np.float64).ravel()
    a -= a.mean(); b -= b.mean()
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0: return 0.0
    return float(np.dot(a, b) / (na * nb))

def family_stats(maps: dict) -> dict:
    fams = sorted(maps.keys())
    intra = {}
    for f in fams:
        m = maps[f]; n = m.shape[0]; rs = []
        for i in range(n):
            for j in range(i+1, n): rs.append(pearson_r(m[i], m[j]))
        intra[f] = rs
    intra_mean = {f: float(np.mean(v)) if v else 0.0 for f, v in intra.items()}
    means = {f: maps[f].mean(axis=0) for f in fams}
    inter = {}
    for i, fa in enumerate(fams):
        for fb in fams[i+1:]: inter[f"{fa}_x_{fb}"] = pearson_r(means[fa], means[fb])
    return {
        "intra_family_r": intra,
        "intra_family_r_mean": intra_mean,
        "inter_family_r": inter,
        "inter_family_r_max": float(max(inter.values())) if inter else 0.0,
        "inter_family_r_min": float(min(inter.values())) if inter else 0.0,
    }

def determine_verdict(stats: dict):
    inter = stats["inter_family_r"]; intra_mean = stats["intra_family_r_mean"]
    pass_inter = any(v < 0.7 for v in inter.values())
    pass_intra = all(v > 0.85 for v in intra_mean.values())
    fail_high = all(v > 0.95 for v in inter.values()) if inter else False
    flags = {"passcrit_inter_lt_0p7_any": pass_inter,
             "passcrit_intra_gt_0p85_all": pass_intra,
             "failcrit_inter_gt_0p95_any": fail_high}
    if fail_high: v = "T1_FAIL"
    elif pass_inter and pass_intra: v = "T1_PASS"
    else: v = "T1_INCONCLUSIVE_FULL"
    return v, flags

def write_result(out_path: Path, payload: dict):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w") as f: json.dump(payload, f, indent=2, sort_keys=True)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--tribev2-src", required=True)
    ap.add_argument("--n-per-family", type=int, default=16)
    ap.add_argument("--out-result", required=True)
    ap.add_argument("--out-maps", required=True)
    ap.add_argument("--cache-dir", default="./tribe_cache")
    ap.add_argument("--checkpoint", default="facebook/tribev2")
    args = ap.parse_args()

    t0 = time.time()
    out_result = Path(args.out_result); out_maps = Path(args.out_maps)
    cache_dir = Path(args.cache_dir); cache_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "frozen_at": "2026-04-26", "mode": "full", "seed": SEED,
        "n_per_family": args.n_per_family, "n_vertices": N_VERTICES_TARGET,
        "family_to_category": FAMILY_TO_CATEGORY, "checkpoint": args.checkpoint,
        "omega_cycle": {"iteration": 3,
            "step1_design": "frozen H0", "step2_implement": "scripts/*",
            "step3_measure": "pending", "step4_byte_identical": "deterministic prompts only",
            "step5_iterate": "pending"},
        "verdict": "T1_DEFERRED_FORWARD_BLOCKED", "errors": [],
    }

    try:
        selected = select_prompts(Path(args.corpus), args.n_per_family)
        payload["prompt_counts"] = {f: len(v) for f, v in selected.items()}
        log(f"prompts selected: {payload['prompt_counts']}")
    except Exception as e:
        payload["verdict"] = "T1_DEFERRED_CORPUS_BLOCKED"
        payload["errors"].append({"stage":"select_prompts","exc":str(e),"tb":traceback.format_exc()})
        write_result(out_result, payload); return 11

    try:
        np.random.seed(SEED)
        try:
            import torch
            torch.manual_seed(SEED)
            if torch.cuda.is_available(): torch.cuda.manual_seed_all(SEED)
        except Exception: pass
        sys.path.insert(0, args.tribev2_src)
        from tribev2.demo_utils import TribeModel
    except Exception as e:
        payload["verdict"] = "T1_DEFERRED_IMPORT_BLOCKED"
        payload["errors"].append({"stage":"import_tribev2","exc":str(e),"tb":traceback.format_exc()})
        write_result(out_result, payload); return 12

    try:
        log(f"Loading TribeModel from {args.checkpoint} ...")
        model = TribeModel.from_pretrained(args.checkpoint, cache_folder=str(cache_dir))
        log("Model loaded.")
    except Exception as e:
        payload["verdict"] = "T1_DEFERRED_MODEL_LOAD_BLOCKED"
        payload["errors"].append({"stage":"model_load","exc":str(e),"tb":traceback.format_exc()})
        write_result(out_result, payload); return 13

    family_maps = {f: [] for f in FAMILIES}
    n_vertices_actual = None
    for fam in FAMILIES:
        for idx, item in enumerate(selected[fam]):
            txt = item["prompt"] + " " + item["response"]
            stem = safe_filename(item["id"])
            txt_path = cache_dir / f"{stem}.txt"
            txt_path.write_text(txt, encoding="utf-8")
            try:
                events = model.get_events_dataframe(text_path=str(txt_path))
                preds, _ = model.predict(events, verbose=False)
                pmap = aggregate_segments_to_map(preds)
                if n_vertices_actual is None: n_vertices_actual = pmap.shape[0]
                if pmap.shape[0] != n_vertices_actual:
                    raise ValueError(f"vertex-count mismatch: {pmap.shape[0]} vs {n_vertices_actual}")
                family_maps[fam].append(pmap)
                log(f"OK {fam}[{idx+1}/{args.n_per_family}] id={item['id']} segs={preds.shape[0]} verts={pmap.shape[0]}")
            except Exception as e:
                payload["errors"].append({"stage":"predict","family":fam,"id":item["id"],
                                          "exc":str(e), "tb":traceback.format_exc()[-2000:]})
                log(f"FAIL {fam} id={item['id']}: {e!r}")

    arrs = {}
    for fam in FAMILIES:
        if not family_maps[fam]:
            payload["verdict"] = "T1_DEFERRED_PREDICT_BLOCKED"
            payload["errors"].append({"stage":"stack_family","family":fam,"exc":"no successful predictions"})
            write_result(out_result, payload); return 14
        arrs[fam] = np.stack(family_maps[fam], axis=0)
        log(f"family={fam} stacked shape={arrs[fam].shape}")

    payload["n_vertices"] = int(n_vertices_actual or N_VERTICES_TARGET)
    out_maps.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out_maps, **arrs)
    log(f"maps written: {out_maps}")

    stats = family_stats(arrs)
    verdict, flags = determine_verdict(stats)
    payload["stats"] = stats; payload.update(flags); payload["verdict"] = verdict
    payload["family_mean_map_sha256"] = {
        f: hashlib.sha256(arrs[f].mean(axis=0).astype(np.float32).tobytes()).hexdigest()
        for f in FAMILIES
    }
    payload["elapsed_seconds"] = round(time.time() - t0, 2)
    payload["omega_cycle"]["step3_measure"] = (
        f"4 family x {args.n_per_family} prompt x {payload['n_vertices']} vertex"
    )
    payload["omega_cycle"]["step5_iterate"] = "verdict written"
    write_result(out_result, payload)
    log(f"verdict={verdict} elapsed={payload['elapsed_seconds']}s")
    return 0

if __name__ == "__main__":
    sys.exit(main())

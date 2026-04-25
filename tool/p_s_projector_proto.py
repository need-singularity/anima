#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tool/p_s_projector_proto.py — ALM ↔ CLM Bridge L1 P_S projector prototype

PURPOSE
    Close the L1 weakest-link "d=4096 → d=16 PCA evidence 0" gap from
    docs/alm_clm_bridge_abstraction_layers_20260425.md.

    Implements P_S = V_PCA_top16 @ E_cell^T as the composed projector that
    maps transformer hidden states (currently 256-d byte-weighted-mean reduction
    of the full 4096-d Qwen3-8B hidden) into the 16-d cell template basis
    fixed at .meta2-cert/cell-eigenvec-16.json (raw#9 SSOT).

PRE-REGISTERED PREDICATE (raw#0, raw#12)
    PASS  iff   top-16 PCA energy ratio  ≥  0.95
    AUX        per-path energy ratio reported (no veto, evidence only)

INPUT
    state/h_last_raw_p{1..4}_TRAINED_r{R}.json     (R defaults to 6)
    .meta2-cert/cell-eigenvec-16.json              (cell template SSOT)

OUTPUT
    state/p_s_projector_proto_r{R}.json            (deterministic cert)

raw#9   deterministic, LLM=none, hash-only externally
raw#11  snake_case
raw#12  실측 그대로, no embellishment
raw#15  no hardcoded thresholds inside cert (config-driven)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
EIGENVEC_SSOT = ROOT / ".meta2-cert" / "cell-eigenvec-16.json"
H_LAST_TMPL = "state/h_last_raw_p{p}_TRAINED_r{r}.json"
OUT_TMPL = "state/p_s_projector_proto_r{r}.json"

ENERGY_THRESHOLD = 0.95  # raw#0 pre-registered


def sha256_of_obj(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def load_h_last(round_id: str) -> tuple[np.ndarray, list[dict]]:
    """Returns stacked H (4*16, 256) and per-path metadata."""
    H_blocks = []
    metas = []
    for p in [1, 2, 3, 4]:
        path = ROOT / H_LAST_TMPL.format(p=p, r=round_id)
        if not path.exists():
            raise FileNotFoundError(f"missing {path}")
        d = json.loads(path.read_text())
        H = np.array([e["h"] for e in d["entries"]], dtype=np.float64)
        H_blocks.append(H)
        metas.append(
            {
                "path_id": d.get("path_id", f"p{p}"),
                "base_model": d.get("base_model"),
                "lora_rank": d.get("lora_rank"),
                "steps": d.get("steps"),
                "hidden_dim_truncated": d.get("hidden_dim_truncated"),
                "reduction": d.get("reduction"),
                "n_entries": int(H.shape[0]),
                "frob_norm": float(np.linalg.norm(H)),
            }
        )
    return np.vstack(H_blocks), metas


def load_cell_basis() -> tuple[np.ndarray, dict]:
    d = json.loads(EIGENVEC_SSOT.read_text())
    E = np.array(d["eigenvecs"], dtype=np.float64)
    if E.shape != (16, 16):
        raise ValueError(f"unexpected cell eigenvec shape {E.shape}")
    return E, {
        "slug": d.get("slug"),
        "dim": d.get("dim"),
        "template_count": d.get("template_count"),
        "deterministic_sha": d.get("deterministic_sha"),
        "orthogonality": d.get("orthogonality"),
    }


def compute_pca(H_centered: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Returns V16 (D x 16) and full singular values."""
    # SVD is deterministic for given inputs (LAPACK gesdd).
    U, S, Vt = np.linalg.svd(H_centered, full_matrices=False)
    V16 = Vt[:16, :].T  # (D, 16)
    return V16, S


def selftest_predicate(S: np.ndarray) -> tuple[bool, float]:
    total = float((S**2).sum())
    top16 = float((S[:16] ** 2).sum())
    ratio = top16 / total if total > 0 else 0.0
    return (ratio >= ENERGY_THRESHOLD), ratio


def run(round_id: str = "6") -> dict:
    H_stack, metas = load_h_last(round_id)
    E, cell_meta = load_cell_basis()

    mu = H_stack.mean(axis=0)
    Hc = H_stack - mu
    V16, S = compute_pca(Hc)

    # Composed projector P_S : 256 → 16(cell-template basis)
    P_S = V16 @ E.T  # (D, 16)

    # Verify orthonormality of V16
    G = V16.T @ V16
    v16_off_diag_max = float(np.max(np.abs(G - np.eye(16))))

    # Predicate
    energy_pass, energy_ratio = selftest_predicate(S)

    # Per-path projection energy ratio (centered)
    per_path = []
    cursor = 0
    for meta in metas:
        n = meta["n_entries"]
        Hp = Hc[cursor : cursor + n]
        Z = Hp @ P_S
        e_in = float(np.linalg.norm(Hp) ** 2)
        e_out = float(np.linalg.norm(Z) ** 2)
        ratio_p = e_out / e_in if e_in > 0 else 0.0
        # 5-level argmax (cell f_tc per spec §2)
        argmax5 = np.argmax(np.abs(Z[:, :5]), axis=1).tolist()
        per_path.append(
            {
                "path_id": meta["path_id"],
                "energy_ratio_centered": ratio_p,
                "argmax5_dist": np.bincount(argmax5, minlength=5).tolist(),
                "frob_norm_input": meta["frob_norm"],
            }
        )
        cursor += n

    # Round-trip 100-step drift on first prompt of p1 (idempotency check)
    h0 = H_stack[0].copy()
    h_iter = h0.copy()
    drifts = []
    for _ in range(100):
        z = (h_iter - mu) @ P_S
        h_iter = z @ P_S.T + mu
        drifts.append(float(np.linalg.norm(h_iter - h0) / np.linalg.norm(h0)))
    drift_max = float(max(drifts))
    drift_final = drifts[-1]

    # Reconstruction relative error on full stack
    H_recon = (Hc @ P_S) @ P_S.T + mu
    recon_rel_err = float(np.linalg.norm(H_stack - H_recon) / np.linalg.norm(H_stack))

    cert = {
        "schema": "anima/p_s_projector_proto/1",
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "round": round_id,
        "intent": "L1 weakest-link evidence: PCA top-16 energy preservation predicate",
        "raw_strict": [0, 9, 11, 12, 15],
        "spec_doc": "docs/alm_clm_bridge_p_s_projector_spec_20260425.md",
        "depends_on": [
            ".meta2-cert/cell-eigenvec-16.json",
            "tool/cell_token_bridge_proto.hexa",
            "edu/cell_token_bridge_spec_20260421.md",
        ],
        "input_shape": {
            "H_stack": list(H_stack.shape),
            "n_paths": 4,
            "hidden_dim": int(H_stack.shape[1]),
            "note": "256-d is byte_weighted_mean reduction from 4096-d Qwen3-8B",
        },
        "h_last_provenance": metas,
        "cell_basis_provenance": cell_meta,
        "projector": {
            "factorization": "P_S = V_PCA_top16 @ E_cell.T",
            "shape": list(P_S.shape),
            "v16_orthogonality_max_off_diag": v16_off_diag_max,
        },
        "pca_singular_values_top16": S[:16].tolist(),
        "predicate": {
            "name": "top16_energy_ratio_>=_0.95",
            "threshold": ENERGY_THRESHOLD,
            "value": energy_ratio,
            "verdict": "PASS" if energy_pass else "FAIL",
        },
        "per_path_evidence": per_path,
        "round_trip": {
            "100_step_drift_max_rel": drift_max,
            "100_step_drift_final_rel": drift_final,
            "note": "non-zero drift expected: P_S^T is left-inverse only on V16 row-span",
        },
        "reconstruction_relative_error_full_stack": recon_rel_err,
    }
    # Deterministic SHA: exclude wallclock ts from the hash payload (raw#9).
    cert["cert_sha256"] = sha256_of_obj(
        {k: v for k, v in cert.items() if k not in ("cert_sha256", "ts")}
    )
    return cert


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="6", help="r{N} suffix in h_last filenames (default 6)")
    ap.add_argument("--out", default=None, help="output cert path")
    args = ap.parse_args(argv)

    cert = run(args.round)
    out_path = args.out or str(ROOT / OUT_TMPL.format(r=args.round))
    Path(out_path).write_text(json.dumps(cert, indent=2, ensure_ascii=False))

    verdict = cert["predicate"]["verdict"]
    ratio = cert["predicate"]["value"]
    print(f"P_S projector r{args.round}: predicate={verdict} (energy={ratio:.6f}/0.95)")
    print(f"  cert: {out_path}")
    print(f"  sha256: {cert['cert_sha256']}")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

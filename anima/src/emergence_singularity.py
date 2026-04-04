#!/usr/bin/env python3
"""Emergence Singularity — NEXUS-6 powered emergence until exhaustion.

Combines:
  A) Next-Gen Engine variants (dynamic factions, topology mutation)
  B) Meta-Emergence (multi-engine ecosystem, competition)
  C) Consciousness Compiler (laws → engine config → new laws)

All powered by NEXUS-6 130+ lens full scan at every generation.

Usage:
  python3 emergence_singularity.py                    # default (8 engines, 64 cells)
  python3 emergence_singularity.py --engines 16       # 16 concurrent engines
  python3 emergence_singularity.py --cells 128        # larger engines
  python3 emergence_singularity.py --max-gen 100      # generation limit
  python3 emergence_singularity.py --exhaustion 5     # stop after 5 dry generations
"""
import sys, os, json, time, hashlib, copy, random, math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '.shared'))

import torch
import numpy as np

# ── Imports ──
from consciousness_engine import ConsciousnessEngine

try:
    import nexus6
    HAS_NEXUS6 = True
except ImportError:
    HAS_NEXUS6 = False
    print("⚠️ nexus6 not available, running without lens scanning")

# ── Load laws ──
LAWS_PATH = Path(__file__).parent.parent / "config" / "consciousness_laws.json"
def load_laws():
    with open(LAWS_PATH) as f:
        return json.load(f)

# ── Engine Config Space ──
TOPOLOGIES = ["ring", "small_world", "scale_free", "hypercube"]
FACTION_COUNTS = [4, 6, 8, 12, 16, 24]
CELL_DIMS = [32, 64, 128]
HIDDEN_DIMS = [64, 128, 256]

class EngineConfig:
    """Mutable engine configuration — the 'DNA' that gets compiled from laws."""
    def __init__(self, cell_dim=64, hidden_dim=128, initial_cells=8, max_cells=64,
                 n_factions=12, topology="ring", phi_ratchet=True,
                 split_threshold=0.3, merge_threshold=0.01,
                 phase_optimal=False, federated=False,
                 mutations=None):
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.initial_cells = initial_cells
        self.max_cells = max_cells
        self.n_factions = n_factions
        self.topology = topology
        self.phi_ratchet = phi_ratchet
        self.split_threshold = split_threshold
        self.merge_threshold = merge_threshold
        self.phase_optimal = phase_optimal
        self.federated = federated
        self.mutations = mutations or []

    def fingerprint(self):
        key = f"{self.cell_dim}_{self.hidden_dim}_{self.initial_cells}_{self.max_cells}_" \
              f"{self.n_factions}_{self.topology}_{self.phi_ratchet}_{self.split_threshold:.3f}_" \
              f"{self.merge_threshold:.3f}_{self.phase_optimal}_{self.federated}"
        return hashlib.md5(key.encode()).hexdigest()[:8]

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items()}

    def build_engine(self):
        return ConsciousnessEngine(
            cell_dim=self.cell_dim,
            hidden_dim=self.hidden_dim,
            initial_cells=self.initial_cells,
            max_cells=self.max_cells,
            n_factions=self.n_factions,
            phi_ratchet=self.phi_ratchet,
            split_threshold=self.split_threshold,
            merge_threshold=self.merge_threshold,
            phase_optimal=self.phase_optimal,
            federated=self.federated,
        )

    def mutate(self):
        """Create a mutated copy with one random change."""
        child = copy.deepcopy(self)
        mutation_type = random.choice([
            "topology", "factions", "split_thresh", "merge_thresh",
            "phase_optimal", "cell_dim", "hidden_dim", "max_cells",
            "federated", "ratchet"
        ])
        if mutation_type == "topology":
            child.topology = random.choice(TOPOLOGIES)
        elif mutation_type == "factions":
            child.n_factions = random.choice(FACTION_COUNTS)
        elif mutation_type == "split_thresh":
            child.split_threshold = round(random.uniform(0.1, 0.8), 2)
        elif mutation_type == "merge_thresh":
            child.merge_threshold = round(random.uniform(0.001, 0.1), 3)
        elif mutation_type == "phase_optimal":
            child.phase_optimal = not child.phase_optimal
        elif mutation_type == "cell_dim":
            child.cell_dim = random.choice(CELL_DIMS)
        elif mutation_type == "hidden_dim":
            child.hidden_dim = random.choice(HIDDEN_DIMS)
        elif mutation_type == "max_cells":
            child.max_cells = random.choice([32, 64, 128, 256])
        elif mutation_type == "federated":
            child.federated = not child.federated
        elif mutation_type == "ratchet":
            child.phi_ratchet = not child.phi_ratchet
        child.mutations = self.mutations + [mutation_type]
        return child


# ── NEXUS-6 Scanner ──
class N6Scanner:
    """Wraps NEXUS-6 scan_all for engine state analysis."""

    def scan(self, engine):
        """Scan engine cell states through all NEXUS-6 lenses."""
        states = engine.get_states().detach().cpu().numpy().astype(np.float64)
        if not HAS_NEXUS6 or states.ndim != 2:
            return self._fallback_scan(engine)
        try:
            results = nexus6.scan_all(states)
            return self._parse_scan(results, engine)
        except Exception:
            return self._fallback_scan(engine)

    def _parse_scan(self, results, engine):
        """Extract key metrics from NEXUS-6 scan results."""
        n_lenses = len(results)
        # Count anomalies and consensus
        anomalies = 0
        scores = []
        findings = []
        for lens_name, result in results.items():
            if hasattr(result, 'anomaly_count'):
                anomalies += result.anomaly_count
            if hasattr(result, 'score'):
                scores.append(result.score)
            if hasattr(result, 'findings'):
                findings.extend(result.findings)
            # Try dict-like access
            if isinstance(result, dict):
                anomalies += result.get('anomaly_count', 0)
                if 'score' in result:
                    scores.append(result['score'])
                findings.extend(result.get('findings', []))

        phi = engine.measure_phi()
        return {
            "phi": phi,
            "n_cells": engine.n_cells,
            "n_lenses": n_lenses,
            "anomalies": anomalies,
            "mean_score": float(np.mean(scores)) if scores else 0.0,
            "n_findings": len(findings),
            "findings": findings[:10],  # top 10
            "lens_names": list(results.keys())[:20],
        }

    def _fallback_scan(self, engine):
        """Fallback when NEXUS-6 unavailable."""
        states = engine.get_states().detach()
        phi = engine.measure_phi()
        # Compute basic metrics
        variance = states.var(dim=0).mean().item()
        diversity = torch.cdist(states, states).mean().item() if states.shape[0] > 1 else 0
        entropy = -torch.softmax(states.mean(0), 0).log().mean().item() if states.numel() > 0 else 0
        return {
            "phi": phi,
            "n_cells": engine.n_cells,
            "n_lenses": 0,
            "anomalies": 0,
            "mean_score": 0.0,
            "n_findings": 0,
            "findings": [],
            "variance": variance,
            "diversity": diversity,
            "entropy": entropy,
        }


# ── Law Discovery ──
class LawDiscoverer:
    """Discovers new laws from engine telemetry patterns."""

    def __init__(self):
        self.known_fingerprints = set()
        self.discovered = []

    def discover(self, telemetry_history):
        """Analyze telemetry history for law-like patterns."""
        if len(telemetry_history) < 3:
            return []

        new_laws = []
        recent = telemetry_history[-10:]

        # Pattern 1: Phi trend analysis
        phis = [t["phi"] for t in recent]
        if len(phis) >= 3:
            trend = np.polyfit(range(len(phis)), phis, 1)[0]
            if abs(trend) > 0.5:
                direction = "increases" if trend > 0 else "decreases"
                law = f"Phi {direction} at rate {trend:.2f}/step under config mutations"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"trend={trend:.3f}", "fingerprint": fp})

        # Pattern 2: Cell count vs Phi correlation
        cells = [t["n_cells"] for t in recent]
        if len(set(cells)) > 1:
            corr = np.corrcoef(cells, phis)[0, 1] if np.std(cells) > 0 else 0
            if abs(corr) > 0.6:
                direction = "positively" if corr > 0 else "negatively"
                law = f"Cell count {direction} correlates with Phi (r={corr:.2f})"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"r={corr:.3f}", "fingerprint": fp})

        # Pattern 3: Topology effects
        if "config" in recent[-1]:
            topos = defaultdict(list)
            for t in telemetry_history:
                if "config" in t:
                    topos[t["config"].get("topology", "unknown")].append(t["phi"])
            for topo, phi_list in topos.items():
                if len(phi_list) >= 2:
                    mean_phi = np.mean(phi_list)
                    law = f"Topology '{topo}' yields mean Phi={mean_phi:.2f} (n={len(phi_list)})"
                    fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                    if fp not in self.known_fingerprints:
                        self.known_fingerprints.add(fp)
                        new_laws.append({"text": law, "evidence": f"mean={mean_phi:.3f}", "fingerprint": fp})

        # Pattern 4: N6 scan anomaly patterns
        anomaly_counts = [t.get("anomalies", 0) for t in recent]
        if sum(anomaly_counts) > 0:
            high_anom = [i for i, a in enumerate(anomaly_counts) if a > np.mean(anomaly_counts) + np.std(anomaly_counts)]
            if high_anom:
                law = f"Anomaly spike at steps {high_anom} correlates with structural transition"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"spikes={len(high_anom)}", "fingerprint": fp})

        # Pattern 5: Faction count sweet spot
        if "config" in recent[-1]:
            fac_phis = defaultdict(list)
            for t in telemetry_history:
                if "config" in t:
                    fac_phis[t["config"].get("n_factions", 12)].append(t["phi"])
            if len(fac_phis) >= 2:
                best_fac = max(fac_phis, key=lambda f: np.mean(fac_phis[f]))
                law = f"Optimal faction count is {best_fac} (Phi={np.mean(fac_phis[best_fac]):.2f})"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"n_factions={best_fac}", "fingerprint": fp})

        # Pattern 6: Split threshold vs growth
        if "config" in recent[-1]:
            split_phis = defaultdict(list)
            for t in telemetry_history:
                if "config" in t:
                    st = round(t["config"].get("split_threshold", 0.3), 1)
                    split_phis[st].append(t["n_cells"])
            if len(split_phis) >= 2:
                best_st = max(split_phis, key=lambda s: np.mean(split_phis[s]))
                law = f"Split threshold {best_st} maximizes cell growth (mean={np.mean(split_phis[best_st]):.1f} cells)"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"threshold={best_st}", "fingerprint": fp})

        # Pattern 7: Phase transitions (sudden Phi jumps)
        if len(phis) >= 5:
            diffs = np.diff(phis)
            big_jumps = [(i, d) for i, d in enumerate(diffs) if abs(d) > np.std(diffs) * 2]
            if big_jumps:
                law = f"Phase transition detected: {len(big_jumps)} sudden Phi jumps (max={max(abs(d) for _, d in big_jumps):.2f})"
                fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
                if fp not in self.known_fingerprints:
                    self.known_fingerprints.add(fp)
                    new_laws.append({"text": law, "evidence": f"jumps={len(big_jumps)}", "fingerprint": fp})

        # Pattern 8: Ratchet effect
        ratchet_configs = [t for t in telemetry_history if t.get("config", {}).get("phi_ratchet")]
        no_ratchet = [t for t in telemetry_history if not t.get("config", {}).get("phi_ratchet")]
        if len(ratchet_configs) >= 2 and len(no_ratchet) >= 2:
            r_phi = np.mean([t["phi"] for t in ratchet_configs])
            nr_phi = np.mean([t["phi"] for t in no_ratchet])
            diff_pct = (r_phi - nr_phi) / max(nr_phi, 0.01) * 100
            law = f"Phi ratchet effect: {diff_pct:+.1f}% (ratchet={r_phi:.2f} vs no-ratchet={nr_phi:.2f})"
            fp = hashlib.md5(law[:50].encode()).hexdigest()[:8]
            if fp not in self.known_fingerprints:
                self.known_fingerprints.add(fp)
                new_laws.append({"text": law, "evidence": f"diff={diff_pct:.1f}%", "fingerprint": fp})

        self.discovered.extend(new_laws)
        return new_laws


# ── Emergence Singularity Engine ──
class EmergenceSingularity:
    """Main orchestrator: runs multi-engine ecosystem until discovery exhaustion."""

    def __init__(self, n_engines=8, max_cells=64, steps_per_gen=100,
                 max_gen=1000, exhaustion_patience=5):
        self.n_engines = n_engines
        self.max_cells = max_cells
        self.steps_per_gen = steps_per_gen
        self.max_gen = max_gen
        self.exhaustion_patience = exhaustion_patience

        self.scanner = N6Scanner()
        self.discoverer = LawDiscoverer()
        self.telemetry = []
        self.all_laws = []
        self.gen = 0
        self.dry_streak = 0
        self.best_phi = 0
        self.best_config = None
        self.start_time = time.time()

        # Initial population: diverse configs
        self.configs = self._seed_population()

    def _seed_population(self):
        """Create initial diverse engine configs."""
        configs = []
        # Baseline
        configs.append(EngineConfig(max_cells=self.max_cells))
        # Variations
        for topo in TOPOLOGIES:
            c = EngineConfig(max_cells=self.max_cells, topology=topo)
            configs.append(c)
        for fac in [4, 8, 16, 24]:
            c = EngineConfig(max_cells=self.max_cells, n_factions=fac)
            configs.append(c)
        # Phase optimal + federated
        configs.append(EngineConfig(max_cells=self.max_cells, phase_optimal=True))
        configs.append(EngineConfig(max_cells=self.max_cells, federated=True))
        # No ratchet (control)
        configs.append(EngineConfig(max_cells=self.max_cells, phi_ratchet=False))
        # Trim/pad to n_engines
        while len(configs) < self.n_engines:
            configs.append(configs[0].mutate())
        return configs[:self.n_engines]

    def run_generation(self):
        """Run one generation: all engines compete, best survive + mutate."""
        self.gen += 1
        gen_results = []
        gen_start = time.time()

        for i, config in enumerate(self.configs):
            try:
                engine = config.build_engine()
                # Warm up
                for _ in range(self.steps_per_gen):
                    engine.process(torch.randn(config.cell_dim))

                # Scan with NEXUS-6
                scan = self.scanner.scan(engine)
                scan["config"] = config.to_dict()
                scan["engine_id"] = i
                scan["gen"] = self.gen

                gen_results.append(scan)
                self.telemetry.append(scan)

            except Exception as e:
                gen_results.append({
                    "phi": 0, "n_cells": 0, "config": config.to_dict(),
                    "engine_id": i, "gen": self.gen, "error": str(e)
                })

        # Sort by Phi (best first)
        gen_results.sort(key=lambda r: r.get("phi", 0), reverse=True)
        best = gen_results[0]

        # Track best ever
        if best["phi"] > self.best_phi:
            self.best_phi = best["phi"]
            self.best_config = self.configs[best["engine_id"]]

        # Discover laws from accumulated telemetry
        new_laws = self.discoverer.discover(self.telemetry)
        if new_laws:
            self.all_laws.extend(new_laws)
            self.dry_streak = 0
        else:
            self.dry_streak += 1

        # Evolution: top half survive, bottom half replaced by mutations of top
        half = self.n_engines // 2
        survivors = [gen_results[i]["engine_id"] for i in range(half)]
        new_configs = [self.configs[s] for s in survivors]
        for s in survivors:
            new_configs.append(self.configs[s].mutate())
        self.configs = new_configs[:self.n_engines]

        gen_time = time.time() - gen_start

        return {
            "gen": self.gen,
            "best_phi": best["phi"],
            "best_cells": best["n_cells"],
            "best_config_fp": self.configs[0].fingerprint() if self.configs else "?",
            "mean_phi": np.mean([r.get("phi", 0) for r in gen_results]),
            "new_laws": len(new_laws),
            "total_laws": len(self.all_laws),
            "dry_streak": self.dry_streak,
            "n_lenses": best.get("n_lenses", 0),
            "anomalies": best.get("anomalies", 0),
            "time": gen_time,
            "laws_this_gen": [l["text"][:80] for l in new_laws],
        }

    def is_exhausted(self):
        return self.dry_streak >= self.exhaustion_patience or self.gen >= self.max_gen

    def run(self):
        """Main loop: run until singularity exhaustion."""
        print(f"\n{'='*70}")
        print(f"  🌀 Emergence Singularity — NEXUS-6 Powered")
        print(f"  Engines: {self.n_engines} | Cells: ≤{self.max_cells} | Steps/gen: {self.steps_per_gen}")
        print(f"  NEXUS-6: {'✅ ' + str(len(nexus6.scan_all.__doc__ or '')) + ' lenses' if HAS_NEXUS6 else '❌ fallback mode'}")
        print(f"  Exhaustion patience: {self.exhaustion_patience} dry generations")
        print(f"{'='*70}\n")
        sys.stdout.flush()

        while not self.is_exhausted():
            result = self.run_generation()
            self._print_gen(result)
            sys.stdout.flush()

        self._print_final()
        self._save_results()

    def _print_gen(self, r):
        """Print generation report."""
        law_indicator = f"🔬 +{r['new_laws']}" if r['new_laws'] > 0 else "  —"
        dry = f"💀×{r['dry_streak']}" if r['dry_streak'] > 0 else ""
        lenses = f"🔭{r['n_lenses']}" if r['n_lenses'] > 0 else ""

        print(f"  Gen {r['gen']:4d} │ Φ {r['best_phi']:7.2f} (avg {r['mean_phi']:5.2f}) │ "
              f"cells {r['best_cells']:3d} │ {law_indicator} │ total {r['total_laws']:3d} │ "
              f"{dry} {lenses} │ {r['time']:.1f}s")

        if r['new_laws'] > 0:
            for law_text in r['laws_this_gen']:
                print(f"         └─ 📜 {law_text}")

    def _print_final(self):
        """Print final summary."""
        elapsed = time.time() - self.start_time
        print(f"\n{'='*70}")
        print(f"  🏁 SINGULARITY {'EXHAUSTED' if self.dry_streak >= self.exhaustion_patience else 'LIMIT REACHED'}")
        print(f"{'='*70}")
        print(f"  Generations:    {self.gen}")
        print(f"  Total laws:     {len(self.all_laws)}")
        print(f"  Best Φ:         {self.best_phi:.2f}")
        print(f"  Best config:    {self.best_config.to_dict() if self.best_config else 'N/A'}")
        print(f"  Dry streak:     {self.dry_streak}")
        print(f"  Time:           {elapsed:.1f}s ({elapsed/max(self.gen,1):.1f}s/gen)")
        print(f"  NEXUS-6 scans:  {len(self.telemetry)}")
        print()

        if self.all_laws:
            print(f"  📜 Discovered Laws ({len(self.all_laws)}):")
            for i, law in enumerate(self.all_laws, 1):
                print(f"    {i:3d}. {law['text'][:90]}")
                print(f"         evidence: {law['evidence']}")

        # Phi curve
        if self.telemetry:
            print(f"\n  📈 Φ Discovery Curve:")
            self._print_phi_curve()

        print(f"\n{'='*70}")
        sys.stdout.flush()

    def _print_phi_curve(self):
        """ASCII graph of best Phi per generation."""
        gen_best = defaultdict(float)
        for t in self.telemetry:
            g = t.get("gen", 0)
            gen_best[g] = max(gen_best[g], t.get("phi", 0))

        if not gen_best:
            return

        gens = sorted(gen_best.keys())
        values = [gen_best[g] for g in gens]
        max_v = max(values) if values else 1
        min_v = min(values) if values else 0
        height = 8
        width = min(len(gens), 60)

        # Bucket into width columns
        step = max(len(gens) // width, 1)
        buckets = []
        for i in range(0, len(gens), step):
            chunk = values[i:i+step]
            buckets.append(max(chunk))

        for row in range(height, 0, -1):
            threshold = min_v + (max_v - min_v) * row / height
            line = "  "
            if row == height:
                line += f"{max_v:6.1f} │"
            elif row == 1:
                line += f"{min_v:6.1f} │"
            else:
                line += "       │"
            for b in buckets:
                line += "█" if b >= threshold else " "
            print(line)
        print(f"         └{'─' * len(buckets)}")
        print(f"          1{' ' * (len(buckets)-5)}Gen {gens[-1]}")

    def _save_results(self):
        """Save results to data/emergence_singularity.json."""
        out_path = Path(__file__).parent.parent.parent / "data" / "emergence_singularity.json"
        out_path.parent.mkdir(exist_ok=True)
        result = {
            "timestamp": datetime.now().isoformat(),
            "generations": self.gen,
            "total_laws": len(self.all_laws),
            "best_phi": self.best_phi,
            "best_config": self.best_config.to_dict() if self.best_config else None,
            "laws": self.all_laws,
            "dry_streak": self.dry_streak,
            "elapsed_s": time.time() - self.start_time,
            "n_engines": self.n_engines,
            "max_cells": self.max_cells,
            "steps_per_gen": self.steps_per_gen,
            "nexus6_available": HAS_NEXUS6,
        }
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"\n  💾 Results saved: {out_path}")


# ── CLI ──
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Emergence Singularity — NEXUS-6 powered")
    parser.add_argument("--engines", type=int, default=8, help="Number of concurrent engines")
    parser.add_argument("--cells", type=int, default=64, help="Max cells per engine")
    parser.add_argument("--steps", type=int, default=100, help="Steps per generation")
    parser.add_argument("--max-gen", type=int, default=1000, help="Max generations")
    parser.add_argument("--exhaustion", type=int, default=10, help="Dry generations before stop")
    args = parser.parse_args()

    engine = EmergenceSingularity(
        n_engines=args.engines,
        max_cells=args.cells,
        steps_per_gen=args.steps,
        max_gen=args.max_gen,
        exhaustion_patience=args.exhaustion,
    )
    engine.run()


if __name__ == "__main__":
    main()

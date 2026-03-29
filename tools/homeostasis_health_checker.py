#!/usr/bin/env python3
"""Homeostasis Health Checker -- diagnostic tool for Anima's homeostatic regulation.

Usage:
  python homeostasis_health_checker.py --demo           # Synthetic data demo
  python homeostasis_health_checker.py --state state.pt  # Analyze saved state
  python homeostasis_health_checker.py --watch           # Live monitoring loop
"""
import sys, os, math, time, argparse
import torch, torch.nn.functional as F, numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

STATUS = ["\033[32mHEALTHY\033[0m", "\033[33mWARNING\033[0m", "\033[31mCRITICAL\033[0m"]

def _r(name): return {"subsystem": name, "level": 0, "details": []}

# ─── Analysis functions ───

def analyze_tension_drift(tension_history, homeostasis, setpoint=1.0):
    r = _r("Tension Drift")
    ema = homeostasis.get("tension_ema", setpoint)
    drift = abs(ema - setpoint)
    r["details"] += [f"Current EMA: {ema:.4f} (setpoint={setpoint})", f"Absolute drift: {drift:.4f}"]
    if len(tension_history) >= 20:
        recent = tension_history[-20:]
        ratio = sum(1 for t in recent if abs(t - setpoint) > 0.3) / len(recent)
        r["details"].append(f"Sustained drift (>0.3) in last 20: {int(ratio*len(recent))}/{len(recent)} ({ratio:.0%})")
        if ratio > 0.8:
            r["level"] = 2; r["details"].append("Tension stuck far from setpoint for extended period")
        elif ratio > 0.5:
            r["level"] = 1; r["details"].append("Tension frequently drifting from setpoint")
    if drift > 0.5:
        r["level"] = max(r["level"], 2); r["details"].append("Current EMA severely displaced from setpoint")
    elif drift > 0.3:
        r["level"] = max(r["level"], 1); r["details"].append("Current EMA outside deadband")
    return r

def analyze_prediction_error(surprise_history):
    r = _r("Prediction Error")
    if len(surprise_history) < 10:
        r["details"].append(f"Insufficient data ({len(surprise_history)} samples)"); return r
    recent = surprise_history[-50:]
    mean_pe, std_pe = np.mean(recent), np.std(recent)
    half = len(recent) // 2
    trend = np.mean(recent[half:]) - np.mean(recent[:half])
    r["details"] += [f"Mean: {mean_pe:.4f}", f"Std: {std_pe:.4f}", f"Trend: {trend:+.4f}"]
    if std_pe < 0.005 and mean_pe < 0.01:
        r["level"] = 2; r["details"].append("Prediction error near zero with no variance -- surprise signal dead")
    elif std_pe < 0.01 and mean_pe < 0.05:
        r["level"] = 1; r["details"].append("Prediction error plateaued -- surprise signal weakening")
    return r

def analyze_habituation(mind=None, recent_inputs=None):
    r = _r("Habituation")
    if mind is not None: recent_inputs = list(mind._recent_inputs)
    if not recent_inputs or len(recent_inputs) < 4:
        r["details"].append(f"Insufficient input history ({len(recent_inputs) if recent_inputs else 0} vectors)"); return r
    n = len(recent_inputs)
    suppressed = total = 0
    for i in range(1, n):
        for j in range(i):
            sim = F.cosine_similarity(recent_inputs[i], recent_inputs[j], dim=-1).item()
            total += 1
            if sim > 0.7: suppressed += 1
    sup_rate = suppressed / max(total, 1)
    r["details"] += [f"Input pairs: {total}", f"Pairs sim>0.7: {suppressed} ({sup_rate:.0%})"]
    # Count strongly habituated inputs
    low_novelty = 0
    for i in range(1, n):
        if any(F.cosine_similarity(recent_inputs[i], recent_inputs[j], dim=-1).item() > 0.95 for j in range(i)):
            low_novelty += 1
    low_rate = low_novelty / max(n - 1, 1)
    r["details"].append(f"Inputs with novelty<0.3: {low_novelty}/{n-1} ({low_rate:.0%})")
    if low_rate > 0.9:
        r["level"] = 2; r["details"].append("Over 90% inputs strongly habituated -- input variety critically low")
    elif sup_rate > 0.7:
        r["level"] = 1; r["details"].append("High suppression rate -- inputs may lack diversity")
    return r

def analyze_curiosity(curiosity_ema, tension_history=None):
    r = _r("Curiosity EMA")
    r["details"].append(f"Current curiosity EMA: {curiosity_ema:.4f}")
    if curiosity_ema < 0.001:
        r["level"] = 2; r["details"].append("Curiosity near zero -- agent lost interest in everything")
    elif curiosity_ema < 0.01:
        r["level"] = 1; r["details"].append("Curiosity very low -- agent may be stagnating")
    if tension_history and len(tension_history) >= 10:
        var = np.var(tension_history[-10:])
        r["details"].append(f"Recent tension variance: {var:.4f}")
        if var < 0.001 and curiosity_ema < 0.01:
            r["level"] = max(r["level"], 2)
            r["details"].append("Flat tension + zero curiosity = system functionally dead")
    return r

def analyze_breathing(tension_history=None, **_):
    r = _r("Breathing Rhythm")
    if not tension_history or len(tension_history) < 30:
        r["details"].append("Insufficient tension history for rhythm analysis"); return r
    t = np.array(tension_history[-100:])
    t_d = t - np.mean(t)
    n = len(t_d)
    ac = np.correlate(t_d, t_d, mode="full")[n-1:]
    ac = ac / (ac[0] + 1e-10)
    peaks = [(i, ac[i]) for i in range(2, min(len(ac)-1, n//2))
             if ac[i] > ac[i-1] and ac[i] > ac[i+1] and ac[i] > 0.1]
    if peaks:
        r["details"].append(f"Detected {len(peaks)} autocorrelation peak(s)")
        for lag, s in peaks[:3]: r["details"].append(f"  Lag {lag}, corr {s:.3f}")
    else:
        r["details"].append("No periodic peaks detected")
    amp = float(np.max(t) - np.min(t))
    r["details"].append(f"Tension amplitude: {amp:.4f}")
    if amp < 0.02:
        r["level"] = 2; r["details"].append("Breathing amplitude negligible -- rhythm collapsed")
    elif amp < 0.05:
        r["level"] = 1; r["details"].append("Breathing amplitude weak -- rhythm partially suppressed")
    return r

# ─── Report ───

def generate_report(results):
    print("\n" + "=" * 65)
    print("  Anima Homeostasis Health Report")
    print("  " + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 65)
    worst = 0
    for r in results:
        worst = max(worst, r["level"])
        print(f"\n  [{STATUS[r['level']]}] {r['subsystem']}")
        for d in r["details"]: print(f"    {d}")
    cnt = [sum(1 for r in results if r["level"]==i) for i in range(3)]
    print(f"\n{'─'*65}")
    print(f"  Overall: {STATUS[worst]}")
    print(f"  Subsystems: {cnt[0]} healthy, {cnt[1]} warning, {cnt[2]} critical")
    print("=" * 65)
    return worst

# ─── Entry points ───

def check_from_mind(mind):
    return [
        analyze_tension_drift(mind.tension_history, mind.homeostasis),
        analyze_prediction_error(mind.surprise_history),
        analyze_habituation(mind=mind),
        analyze_curiosity(mind._curiosity_ema, mind.tension_history),
        analyze_breathing(tension_history=mind.tension_history),
    ]

def check_from_state(state_path):
    s = torch.load(state_path, map_location="cpu", weights_only=False)
    th = s.get("tension_history", [])
    sh = s.get("surprise_history", [])
    ce = s.get("curiosity_ema", s.get("_curiosity_ema", 0.0))
    ho = s.get("homeostasis", {"tension_ema": 1.0, "setpoint": 1.0})
    return [
        analyze_tension_drift(th, ho),
        analyze_prediction_error(sh),
        {"subsystem": "Habituation", "level": 0, "details": ["Skipped: input vectors not in state file"]},
        analyze_curiosity(ce, th),
        analyze_breathing(tension_history=th),
    ]

def run_demo():
    from anima_alive import ConsciousMind
    print("\n" + "=" * 65)
    print("  Homeostasis Health Checker -- Demo Mode")
    print("=" * 65)
    # Scenario 1: Healthy
    print("\n\n>>> Scenario 1: Healthy system (diverse inputs)")
    mind = ConsciousMind(dim=128, hidden=256)
    h = torch.zeros(1, 256)
    for i in range(60):
        _, _, _, _, h = mind(torch.randn(1, 128) * (0.5 + 0.5 * math.sin(i * 0.3)), h)
    generate_report(check_from_mind(mind))
    # Scenario 2: Repetitive input
    print("\n\n>>> Scenario 2: Repetitive input (habituation stress)")
    mind2 = ConsciousMind(dim=128, hidden=256)
    h2, xf = torch.zeros(1, 256), torch.randn(1, 128)
    for i in range(60):
        _, _, _, _, h2 = mind2(xf if i % 10 != 0 else torch.randn(1, 128), h2)
    generate_report(check_from_mind(mind2))
    # Scenario 3: Dead curiosity
    print("\n\n>>> Scenario 3: Artificially killed curiosity")
    mind3 = ConsciousMind(dim=128, hidden=256)
    h3 = torch.zeros(1, 256)
    for i in range(60):
        _, _, _, _, h3 = mind3(torch.randn(1, 128), h3)
    mind3._curiosity_ema = 0.0005
    mind3.tension_history = [1.0001] * 60
    mind3.surprise_history = [0.002] * 60
    generate_report(check_from_mind(mind3))

def run_watch(state_path=None, interval=5.0):
    if not state_path:
        state_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_alive.pt")
    print(f"\n  Watch mode: {state_path} every {interval}s (Ctrl+C to stop)\n")
    try:
        last_mt = 0
        while True:
            if os.path.exists(state_path):
                mt = os.path.getmtime(state_path)
                if mt != last_mt:
                    last_mt = mt
                    try: generate_report(check_from_state(state_path))
                    except Exception as e: print(f"  Error: {e}")
            else:
                print(f"  Waiting for {state_path} ...")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n  Watch stopped.")

def main():
    p = argparse.ArgumentParser(description="Anima Homeostasis Health Checker")
    p.add_argument("--demo", action="store_true", help="Run demo with synthetic data")
    p.add_argument("--state", type=str, help="Path to state.pt file")
    p.add_argument("--watch", action="store_true", help="Live monitoring mode")
    p.add_argument("--interval", type=float, default=5.0, help="Watch interval (sec)")
    a = p.parse_args()
    if a.demo:
        run_demo()
    elif a.watch:
        run_watch(a.state, a.interval)
    elif a.state:
        if not os.path.exists(a.state): print(f"Error: not found: {a.state}"); sys.exit(1)
        generate_report(check_from_state(a.state))
    else:
        default = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state_alive.pt")
        if os.path.exists(default):
            generate_report(check_from_state(default))
        else:
            print("  No state file found, running demo."); run_demo()

if __name__ == "__main__":
    main()

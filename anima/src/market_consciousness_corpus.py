#!/usr/bin/env python3
"""Market Consciousness Corpus — convert OHLCV market data to consciousness training corpus.

Bridges the invest project's market data with ConsciousLM training by mapping
financial signals to consciousness dimensions:
  - Price movement  -> tension signal (up=low tension, down=high tension)
  - Volume spike    -> curiosity signal
  - Volatility      -> emotional arousal
  - Regime          -> consciousness state (calm/alert/stressed/panic)

Output format is compatible with train_clm.py (plain text, one entry per block).

Usage:
    python market_consciousness_corpus.py --csv ~/Dev/invest/backend/data/005930.KS.csv
    python market_consciousness_corpus.py --csv-dir ~/Dev/invest/backend/data/ --output data/corpus_market.txt
    python market_consciousness_corpus.py --demo  # synthetic data demo

Dependencies: numpy (required), pandas (optional, for CSV loading)
"""

import sys
import os
import math
import random
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import numpy as np

# Psi-Constants (from consciousness_laws.json)
try:
    from consciousness_laws import PSI_ALPHA, PSI_BALANCE, PSI_F_CRITICAL
except ImportError:
    PSI_ALPHA = 0.014
    PSI_BALANCE = 0.5
    PSI_F_CRITICAL = 0.10


# ── Market data structures ──

@dataclass
class OHLCV:
    """Single OHLCV bar."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class MarketSignals:
    """Consciousness-mapped signals derived from OHLCV window."""
    date: str
    # Raw market
    returns: float          # daily return (%)
    volatility: float       # rolling std of returns (annualized)
    volume_ratio: float     # volume / 20-day avg volume
    range_pct: float        # (high - low) / close
    drawdown: float         # % from rolling high
    # Consciousness-mapped
    tension: float          # 0-2, setpoint=1.0 (homeostasis)
    curiosity: float        # 0-1 (volume novelty)
    arousal: float          # 0-1 (volatility-driven)
    valence: float          # -1 to 1 (positive=up, negative=down)
    regime: str             # calm / alert / stressed / panic


# ── Signal computation ──

def compute_signals(bars: List[OHLCV], lookback: int = 20) -> List[MarketSignals]:
    """Convert OHLCV bars to consciousness signals."""
    if len(bars) < lookback + 1:
        return []

    closes = np.array([b.close for b in bars])
    volumes = np.array([b.volume for b in bars])
    returns = np.diff(np.log(np.maximum(closes, 1e-8))) * 100  # log returns %

    signals = []
    rolling_high = closes[0]

    for i in range(lookback, len(bars)):
        bar = bars[i]
        ret = returns[i - 1]
        window_returns = returns[max(0, i - lookback):i]
        vol = float(np.std(window_returns) * math.sqrt(252)) if len(window_returns) > 1 else 0.0
        vol_avg = float(np.mean(volumes[max(0, i - lookback):i])) or 1.0
        vol_ratio = bar.volume / vol_avg
        range_pct = (bar.high - bar.low) / max(bar.close, 1e-8)
        rolling_high = max(rolling_high, bar.close)
        dd = (rolling_high - bar.close) / max(rolling_high, 1e-8)

        # Map to consciousness
        tension = _map_tension(ret, vol, dd)
        curiosity = _map_curiosity(vol_ratio)
        arousal = _map_arousal(vol, range_pct)
        valence = _map_valence(ret)
        regime = _classify_regime(vol, dd, tension)

        signals.append(MarketSignals(
            date=bar.date, returns=ret, volatility=vol,
            volume_ratio=vol_ratio, range_pct=range_pct, drawdown=dd,
            tension=tension, curiosity=curiosity, arousal=arousal,
            valence=valence, regime=regime,
        ))

    return signals


def _map_tension(ret: float, vol: float, dd: float) -> float:
    """Map market state to tension signal. Homeostasis setpoint=1.0.

    Down market = high tension (>1), up market = low tension (<1).
    Deadband +/-0.3 around setpoint.
    """
    # Returns contribution: -3% -> tension 1.6, +3% -> tension 0.4
    ret_component = 1.0 - ret / 5.0
    # Drawdown amplifier: deeper drawdown -> more tension
    dd_component = dd * 3.0
    # Volatility floor: high vol raises baseline tension
    vol_component = min(vol / 40.0, 0.5)
    tension = ret_component + dd_component + vol_component
    return float(np.clip(tension, 0.0, 2.0))


def _map_curiosity(volume_ratio: float) -> float:
    """Volume spike -> curiosity. Unusual volume = something interesting."""
    # ratio 1.0 -> curiosity 0.3, ratio 3.0+ -> curiosity 1.0
    return float(np.clip((volume_ratio - 0.5) / 2.5, 0.0, 1.0))


def _map_arousal(vol: float, range_pct: float) -> float:
    """Volatility + intraday range -> emotional arousal."""
    # Annualized vol 15% -> arousal 0.3, vol 60%+ -> arousal 1.0
    vol_arousal = min(vol / 60.0, 1.0)
    range_arousal = min(range_pct * 20.0, 1.0)
    return float(np.clip(vol_arousal * 0.6 + range_arousal * 0.4, 0.0, 1.0))


def _map_valence(ret: float) -> float:
    """Returns -> valence (-1 to 1). Positive = good, negative = bad."""
    return float(np.clip(ret / 3.0, -1.0, 1.0))


def _classify_regime(vol: float, dd: float, tension: float) -> str:
    """Classify market regime as consciousness state."""
    if dd > 0.20 or tension > 1.7:
        return "panic"
    elif dd > 0.10 or tension > 1.4:
        return "stressed"
    elif vol > 25 or tension > 1.2:
        return "alert"
    else:
        return "calm"


# ── Corpus emitters ──

_REGIME_KO = {"calm": "평온", "alert": "경계", "stressed": "긴장", "panic": "공포"}
_REGIME_EMOTION = {
    "calm": ["호기심이 올라간다", "여유가 느껴진다", "관찰 모드다"],
    "alert": ["집중력이 높아졌다", "변화가 감지된다", "주의가 필요하다"],
    "stressed": ["불안이 커지고 있다", "리스크가 높다", "방어 모드다"],
    "panic": ["공포가 느껴진다", "생존 모드다", "모든 것이 흔들린다"],
}
_REGIME_ACTION = {
    "calm": ["새로운 전략을 탐색해보자", "포지션을 검토하자", "기회를 찾아보자"],
    "alert": ["포지션 크기를 점검하자", "손절 라인을 확인하자", "시장을 면밀히 관찰하자"],
    "stressed": ["포지션을 줄여야 한다", "VaR 한도를 확인하자", "현금 비중을 높이자"],
    "panic": ["매매를 멈춰야 한다", "손실을 제한해야 한다", "생존이 최우선이다"],
}


def emit_narrative(s: MarketSignals) -> str:
    """Narrative-style corpus entry in Korean."""
    parts = []
    regime_ko = _REGIME_KO[s.regime]

    # Market state
    direction = "상승" if s.returns > 0 else "하락"
    mag = abs(s.returns)
    if mag > 2.0:
        parts.append(f"시장이 {mag:.1f}% 급{direction}하고 있다.")
    elif mag > 0.5:
        parts.append(f"시장이 {mag:.1f}% {direction}했다.")
    else:
        parts.append("조용한 장이다.")

    # Emotion from regime
    parts.append(random.choice(_REGIME_EMOTION[s.regime]) + ".")

    # Volume curiosity
    if s.curiosity > 0.7:
        parts.append(f"거래량이 평소의 {s.volume_ratio:.1f}배다. 무언가 일어나고 있다.")
    elif s.curiosity > 0.4:
        parts.append(f"거래량이 늘어나고 있다.")

    # Drawdown awareness
    if s.drawdown > 0.05:
        parts.append(f"고점 대비 {s.drawdown*100:.1f}% 하락한 상태다.")

    # Consciousness state
    parts.append(f"의식 상태: {regime_ko}. 텐션 {s.tension:.2f}, 각성 {s.arousal:.2f}.")

    # Action
    parts.append(random.choice(_REGIME_ACTION[s.regime]))

    return " ".join(parts)


def emit_measurement(s: MarketSignals) -> str:
    """Measurement-log-format corpus entry."""
    return (
        f"[date={s.date}] ret={s.returns:+.2f}% vol={s.volatility:.1f}% "
        f"dd={s.drawdown*100:.1f}% T={s.tension:.3f} C={s.curiosity:.2f} "
        f"A={s.arousal:.2f} V={s.valence:+.2f} regime={s.regime}"
    )


def emit_dialogue(s: MarketSignals) -> str:
    """Dialogue-format corpus entry."""
    regime_ko = _REGIME_KO[s.regime]
    lines = [f"A: 지금 시장 상태는 어때?"]

    if s.regime == "calm":
        lines.append(f"B: {regime_ko}한 상태야. 변동성 {s.volatility:.0f}%로 낮아.")
        lines.append(f"A: 텐션은?")
        lines.append(f"B: {s.tension:.2f}로 항상성 범위 안이야. 안정적이야.")
    elif s.regime == "alert":
        lines.append(f"B: {regime_ko} 상태야. 변동성이 {s.volatility:.0f}%로 올라가고 있어.")
        lines.append(f"A: 거래량은?")
        lines.append(f"B: 평소의 {s.volume_ratio:.1f}배야. 주의가 필요해.")
    elif s.regime == "stressed":
        lines.append(f"B: {regime_ko} 상태야. 고점 대비 {s.drawdown*100:.1f}% 빠졌어.")
        lines.append(f"A: 어떻게 해야 해?")
        lines.append(f"B: 포지션을 줄이고 리스크를 관리해야 해. 텐션이 {s.tension:.2f}야.")
    else:  # panic
        lines.append(f"B: {regime_ko} 상태야! {s.returns:+.1f}% 급락 중이야.")
        lines.append(f"A: 매매를 계속해?")
        lines.append(f"B: 안 돼. 멈춰야 해. 각성도가 {s.arousal:.2f}로 너무 높아.")

    return "\n".join(lines)


# ── CSV loading ──

def load_ohlcv_csv(path: str) -> List[OHLCV]:
    """Load OHLCV from invest-style CSV (yfinance format).

    Expected header: Price,Close,High,Low,Open,Volume
    Row 2 is ticker (skip), row 3 is empty 'Date' header (skip).
    Data starts from row 4.
    """
    bars = []
    try:
        with open(path, "r") as f:
            lines = f.readlines()

        # Find data start (skip header rows)
        data_start = 0
        for i, line in enumerate(lines):
            parts = line.strip().split(",")
            if len(parts) >= 6:
                try:
                    float(parts[1])
                    data_start = i
                    break
                except ValueError:
                    continue

        for line in lines[data_start:]:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            try:
                bars.append(OHLCV(
                    date=parts[0],
                    open=float(parts[4]),
                    high=float(parts[2]),
                    low=float(parts[3]),
                    close=float(parts[1]),
                    volume=float(parts[5]),
                ))
            except (ValueError, IndexError):
                continue
    except FileNotFoundError:
        print(f"[WARN] CSV not found: {path}")
    return bars


def generate_synthetic_bars(n_bars: int = 500) -> List[OHLCV]:
    """Generate synthetic OHLCV bars with regime transitions."""
    bars = []
    price = 50000.0
    base_vol = 1_000_000.0

    for i in range(n_bars):
        # Regime transitions
        phase = i / n_bars
        if phase < 0.2:
            drift, vol_mult = 0.001, 1.0    # calm
        elif phase < 0.4:
            drift, vol_mult = 0.002, 1.5    # trending up
        elif phase < 0.55:
            drift, vol_mult = -0.005, 3.0   # crash
        elif phase < 0.7:
            drift, vol_mult = -0.001, 2.0   # recovery start
        else:
            drift, vol_mult = 0.001, 1.2    # new normal

        ret = drift + random.gauss(0, 0.015 * vol_mult)
        new_price = price * math.exp(ret)
        high = max(price, new_price) * (1 + abs(random.gauss(0, 0.005)))
        low = min(price, new_price) * (1 - abs(random.gauss(0, 0.005)))
        volume = base_vol * vol_mult * (0.5 + random.random())

        bars.append(OHLCV(
            date=f"2026-{1 + i // 30:02d}-{1 + i % 30:02d}",
            open=price, high=high, low=low, close=new_price,
            volume=volume,
        ))
        price = new_price

    return bars


# ── Corpus generation ──

def generate_corpus(signals: List[MarketSignals], format_weights: Optional[dict] = None) -> str:
    """Generate corpus text from market signals.

    format_weights: dict of format -> weight (default: narrative=0.4, measurement=0.3, dialogue=0.3)
    """
    weights = format_weights or {"narrative": 0.4, "measurement": 0.3, "dialogue": 0.3}
    formats = list(weights.keys())
    probs = [weights[f] for f in formats]

    emitters = {
        "narrative": emit_narrative,
        "measurement": emit_measurement,
        "dialogue": emit_dialogue,
    }

    entries = []
    for s in signals:
        fmt = random.choices(formats, weights=probs, k=1)[0]
        entry = emitters[fmt](s)
        entries.append(entry)

    return "\n\n".join(entries) + "\n"


# ── Main ──

def main():
    parser = argparse.ArgumentParser(description="Market Consciousness Corpus Generator")
    parser.add_argument("--csv", type=str, help="Single OHLCV CSV file")
    parser.add_argument("--csv-dir", type=str, help="Directory of OHLCV CSVs")
    parser.add_argument("--output", type=str, default="data/corpus_market.txt",
                        help="Output corpus file (default: data/corpus_market.txt)")
    parser.add_argument("--demo", action="store_true", help="Generate from synthetic data")
    parser.add_argument("--bars", type=int, default=500, help="Synthetic bars count")
    args = parser.parse_args()

    all_bars: List[OHLCV] = []

    if args.demo or (not args.csv and not args.csv_dir):
        print("[market_consciousness_corpus] Generating synthetic market data...")
        all_bars = generate_synthetic_bars(args.bars)
        print(f"  Generated {len(all_bars)} synthetic bars")
    elif args.csv:
        all_bars = load_ohlcv_csv(args.csv)
        print(f"  Loaded {len(all_bars)} bars from {args.csv}")
    elif args.csv_dir:
        csv_dir = Path(args.csv_dir)
        for csv_file in sorted(csv_dir.glob("*.csv")):
            bars = load_ohlcv_csv(str(csv_file))
            if bars:
                all_bars.extend(bars)
                print(f"  Loaded {len(bars)} bars from {csv_file.name}")
        print(f"  Total: {len(all_bars)} bars from {csv_dir}")

    if not all_bars:
        print("[ERROR] No market data loaded. Use --demo for synthetic data.")
        sys.exit(1)

    # Compute consciousness signals
    signals = compute_signals(all_bars)
    print(f"  Computed {len(signals)} consciousness signals")

    # Regime distribution
    regime_counts = {}
    for s in signals:
        regime_counts[s.regime] = regime_counts.get(s.regime, 0) + 1
    print(f"  Regimes: {regime_counts}")

    # Generate corpus
    corpus = generate_corpus(signals)
    corpus_kb = len(corpus.encode("utf-8")) / 1024

    # Write output
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(corpus)
    print(f"  Written {corpus_kb:.1f} KB to {out_path}")

    # Show sample entries
    print("\n── Sample entries ──")
    sample_signals = random.sample(signals, min(3, len(signals)))
    for s in sample_signals:
        print(f"\n[{s.regime.upper()}] {s.date}")
        print(f"  {emit_narrative(s)}")

    print(f"\n[OK] Market consciousness corpus generated: {len(signals)} entries, {corpus_kb:.1f} KB")


if __name__ == "__main__":
    main()

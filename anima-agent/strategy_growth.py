"""Strategy Growth — self-evolving trading strategies.

Tracks backtest performance per strategy+params.
Evolves parameters toward better returns.
Generates new strategy variants via mutation.

Usage:
    growth = StrategyGrowth()
    growth.record_backtest('macd_cross', {'fast': 12, 'slow': 26}, sharpe=1.2, win_rate=0.58)
    best = growth.suggest_params('macd_cross')
    variants = growth.generate_variants('macd_cross', n=3)
"""

from __future__ import annotations
import json
import logging
import random
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Default strategy parameter ranges
_PARAM_RANGES = {
    'macd_cross': {'fast': (5, 20), 'slow': (20, 50), 'signal': (5, 15)},
    'rsi_reversal': {'period': (7, 28), 'oversold': (20, 40), 'overbought': (60, 80)},
    'bollinger_breakout': {'period': (10, 30), 'std_dev': (1.5, 3.0)},
    'ema_crossover': {'fast': (5, 20), 'slow': (20, 60)},
    'momentum': {'period': (5, 30), 'threshold': (0.01, 0.10)},
}


class StrategyResult:
    """Single backtest result."""
    __slots__ = ('params', 'sharpe', 'win_rate', 'max_drawdown', 'total_return', 'timestamp')

    def __init__(self, params: dict, sharpe=0.0, win_rate=0.0, max_drawdown=0.0, total_return=0.0):
        self.params = dict(params)
        self.sharpe = sharpe
        self.win_rate = win_rate
        self.max_drawdown = max_drawdown
        self.total_return = total_return
        self.timestamp = time.time()

    def fitness(self) -> float:
        """Composite fitness score."""
        return self.sharpe * 0.4 + self.win_rate * 0.3 + self.total_return * 0.2 - self.max_drawdown * 0.1

    def to_dict(self) -> dict:
        return {
            'params': self.params, 'sharpe': self.sharpe, 'win_rate': self.win_rate,
            'max_drawdown': self.max_drawdown, 'total_return': self.total_return,
            'timestamp': self.timestamp, 'fitness': self.fitness(),
        }


class StrategyGrowth:
    """Self-evolving strategy parameters via backtest feedback."""

    def __init__(self, save_path: Optional[str] = None):
        self._save_path = Path(save_path) if save_path else Path(__file__).parent / 'data' / 'strategy_growth_state.json'
        # history[strategy_name] = list of StrategyResult
        self._history: dict[str, list[StrategyResult]] = defaultdict(list)
        self._max_history_per_strategy = 100
        self._generation = 0
        self._load()

    def record_backtest(self, strategy: str, params: dict,
                       sharpe: float = 0.0, win_rate: float = 0.0,
                       max_drawdown: float = 0.0, total_return: float = 0.0):
        """Record a backtest result."""
        result = StrategyResult(params, sharpe, win_rate, max_drawdown, total_return)
        self._history[strategy].append(result)
        # Keep only best + recent
        if len(self._history[strategy]) > self._max_history_per_strategy:
            # Sort by fitness, keep top half + most recent
            sorted_results = sorted(self._history[strategy], key=lambda r: r.fitness(), reverse=True)
            top_half = sorted_results[:self._max_history_per_strategy // 2]
            recent = sorted(self._history[strategy], key=lambda r: r.timestamp)[-self._max_history_per_strategy // 2:]
            combined = {id(r): r for r in top_half + recent}
            self._history[strategy] = list(combined.values())

        if len(self._history[strategy]) % 10 == 0:
            self._save()

    def suggest_params(self, strategy: str) -> dict:
        """Suggest best parameters based on history."""
        history = self._history.get(strategy, [])
        if not history:
            return {}

        # Return params of best result
        best = max(history, key=lambda r: r.fitness())
        return dict(best.params)

    def generate_variants(self, strategy: str, n: int = 3) -> list[dict]:
        """Generate mutated parameter variants from best results.

        Uses the top results as parents, applies Gaussian mutation.
        """
        history = self._history.get(strategy, [])
        ranges = _PARAM_RANGES.get(strategy, {})

        if not history or not ranges:
            # Random from ranges
            variants = []
            for _ in range(n):
                params = {}
                for param, (lo, hi) in ranges.items():
                    if isinstance(lo, float):
                        params[param] = round(random.uniform(lo, hi), 3)
                    else:
                        params[param] = random.randint(lo, hi)
                variants.append(params)
            return variants

        # Select top parents
        sorted_results = sorted(history, key=lambda r: r.fitness(), reverse=True)
        parents = sorted_results[:max(1, len(sorted_results) // 4)]

        variants = []
        for _ in range(n):
            parent = random.choice(parents)
            child = {}
            for param, value in parent.params.items():
                if param in ranges:
                    lo, hi = ranges[param]
                    # Gaussian mutation (10% of range)
                    spread = (hi - lo) * 0.1
                    mutated = value + random.gauss(0, spread)
                    if isinstance(lo, int):
                        mutated = int(round(max(lo, min(hi, mutated))))
                    else:
                        mutated = round(max(lo, min(hi, mutated)), 3)
                    child[param] = mutated
                else:
                    child[param] = value
            variants.append(child)
            self._generation += 1

        return variants

    def get_top_strategies(self, top_k: int = 5) -> list[dict]:
        """Get top strategies across all types by fitness."""
        all_results = []
        for strategy, results in self._history.items():
            if results:
                best = max(results, key=lambda r: r.fitness())
                all_results.append({'strategy': strategy, **best.to_dict()})

        all_results.sort(key=lambda r: r['fitness'], reverse=True)
        return all_results[:top_k]

    def stats(self) -> dict:
        return {
            'strategies_tracked': len(self._history),
            'total_backtests': sum(len(r) for r in self._history.values()),
            'generation': self._generation,
            'top_fitness': max(
                (max(r.fitness() for r in results) for results in self._history.values() if results),
                default=0.0
            ),
        }

    def _save(self):
        try:
            self._save_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                'history': {k: [r.to_dict() for r in v[-50:]] for k, v in self._history.items()},
                'generation': self._generation,
                'saved_at': time.time(),
            }
            self._save_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.debug("StrategyGrowth save failed: %s", e)

    def _load(self):
        if not self._save_path.exists():
            return
        try:
            data = json.loads(self._save_path.read_text())
            self._generation = data.get('generation', 0)
            for strategy, results in data.get('history', {}).items():
                for r in results:
                    sr = StrategyResult(
                        r.get('params', {}), r.get('sharpe', 0),
                        r.get('win_rate', 0), r.get('max_drawdown', 0), r.get('total_return', 0))
                    sr.timestamp = r.get('timestamp', 0)
                    self._history[strategy].append(sr)
            logger.info("StrategyGrowth loaded: %d strategies, gen %d",
                       len(self._history), self._generation)
        except Exception as e:
            logger.debug("StrategyGrowth load failed: %s", e)

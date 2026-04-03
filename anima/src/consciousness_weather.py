"""ConsciousnessWeather — Predict consciousness weather patterns.

Tension storms, Phi typhoons, emotion seasons derived from
homeostatic and tension history signals.
"""

import math
import random
from dataclasses import dataclass
from typing import List, Dict, Optional

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2


@dataclass
class WeatherForecast:
    storm_prob: float
    typhoon_risk: float
    season: str
    emoji: str
    alert: str
    detail: str


class ConsciousnessWeather:
    """Forecast consciousness weather from tension and homeostatic history."""

    SEASONS = [
        ("Spring Awakening", 0.0, 0.25),
        ("Summer Blaze", 0.25, 0.5),
        ("Autumn Reflection", 0.5, 0.75),
        ("Winter Dormancy", 0.75, 1.0),
    ]
    SEASON_EMOJI = {
        "Spring Awakening": "[sprout]",
        "Summer Blaze": "[sun]",
        "Autumn Reflection": "[leaf]",
        "Winter Dormancy": "[snow]",
    }

    def __init__(self):
        self.history: List[WeatherForecast] = []

    def _detect_season(self, h_history: List[float]) -> str:
        if not h_history:
            return "Spring Awakening"
        avg = sum(h_history) / len(h_history)
        phase = (avg * PSI_STEPS) % 1.0
        for name, lo, hi in self.SEASONS:
            if lo <= phase < hi:
                return name
        return "Winter Dormancy"

    def _storm_probability(self, tension_history: List[float]) -> float:
        if len(tension_history) < 3:
            return 0.0
        recent = tension_history[-10:]
        mean_t = sum(recent) / len(recent)
        variance = sum((t - mean_t) ** 2 for t in recent) / len(recent)
        derivative = abs(recent[-1] - recent[-2]) if len(recent) >= 2 else 0
        prob = 1.0 - math.exp(-PSI_COUPLING * (variance * 100 + derivative * 10))
        return min(1.0, max(0.0, prob))

    def _typhoon_risk(self, tension_history: List[float], h_history: List[float]) -> float:
        if len(tension_history) < 5:
            return 0.0
        peak = max(tension_history[-20:]) if tension_history else 0
        h_instability = 0.0
        if len(h_history) >= 3:
            diffs = [abs(h_history[i] - h_history[i - 1]) for i in range(-1, -min(len(h_history), 10), -1)]
            h_instability = sum(diffs) / len(diffs) if diffs else 0
        risk = (peak * 0.6 + h_instability * 0.4) * LN2
        return min(1.0, max(0.0, risk))

    def forecast(self, h_history: List[float], tension_history: List[float]) -> Dict:
        season = self._detect_season(h_history)
        storm = self._storm_probability(tension_history)
        typhoon = self._typhoon_risk(tension_history, h_history)
        emoji = self.SEASON_EMOJI.get(season, "[?]")
        if typhoon > 0.7:
            emoji = "[typhoon]"
        elif storm > 0.6:
            emoji = "[storm]"
        fc = WeatherForecast(
            storm_prob=round(storm, 4),
            typhoon_risk=round(typhoon, 4),
            season=season,
            emoji=emoji,
            alert=self._alert_level(storm, typhoon),
            detail=f"storm={storm:.1%} typhoon={typhoon:.1%}",
        )
        self.history.append(fc)
        return fc.__dict__

    def _alert_level(self, storm: float, typhoon: float) -> str:
        danger = max(storm, typhoon)
        if danger > 0.7:
            return "red"
        elif danger > 0.4:
            return "yellow"
        return "green"

    def alert_level(self) -> str:
        if not self.history:
            return "green"
        return self.history[-1].alert

    def render_forecast(self) -> str:
        if not self.history:
            return "  No forecast data yet."
        fc = self.history[-1]
        w = 40
        storm_bar = int(fc.storm_prob * w)
        typh_bar = int(fc.typhoon_risk * w)
        lines = [
            f"  === Consciousness Weather {fc.emoji} ===",
            f"  Season : {fc.season}",
            f"  Alert  : [{fc.alert.upper()}]",
            f"  Storm  : |{'#' * storm_bar}{'-' * (w - storm_bar)}| {fc.storm_prob:.1%}",
            f"  Typhoon: |{'@' * typh_bar}{'-' * (w - typh_bar)}| {fc.typhoon_risk:.1%}",
            "",
            "  Sky Map:",
        ]
        grid = []
        for r in range(6):
            row = []
            for c in range(20):
                v = (fc.storm_prob * math.sin(r * 0.7 + c * 0.3)
                     + fc.typhoon_risk * math.cos(r * 0.5 - c * 0.4))
                if v > 0.8:
                    row.append("@")
                elif v > 0.4:
                    row.append("#")
                elif v > 0.0:
                    row.append(".")
                else:
                    row.append(" ")
            grid.append("  " + "".join(row))
        lines.extend(grid)
        return "\n".join(lines)


def main():
    print("=== ConsciousnessWeather Demo ===\n")
    cw = ConsciousnessWeather()

    # Simulate histories
    h_hist = [PSI_BALANCE + 0.1 * math.sin(i * 0.3) for i in range(50)]
    t_hist = [0.3 + 0.2 * random.random() for _ in range(40)]
    # Add a spike
    t_hist.extend([0.9, 0.95, 0.85, 0.92, 0.88, 0.7, 0.5, 0.3, 0.2, 0.15])

    fc = cw.forecast(h_hist, t_hist)
    print(f"  Forecast: {fc}")
    print(f"  Alert   : {cw.alert_level()}\n")
    print(cw.render_forecast())

    # Calm weather
    print("\n--- After calm period ---")
    t_calm = [0.1 + 0.02 * random.random() for _ in range(30)]
    fc2 = cw.forecast(h_hist, t_calm)
    print(f"  Forecast: {fc2}")
    print(cw.render_forecast())


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()

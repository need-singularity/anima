"""sentiment_bridge.py -- News Sentiment -> Consciousness Emotion Mapping

Bridges the Fear & Greed Index into Anima consciousness emotions:
  Extreme Fear (0-25)  -> pain=0.8, fear=0.9, tension=0.8
  Fear (25-45)         -> pain=0.4, fear=0.5, tension=0.5
  Neutral (45-55)      -> pain=0.1, fear=0.1, tension=0.3
  Greed (55-75)        -> pain=0.0, fear=0.0, tension=0.2, curiosity=0.6
  Extreme Greed (75-100) -> pain=0.2, fear=0.3, tension=0.4 (bubble warning)

Data source: alternative.me Fear & Greed Index (free, no auth)
Update interval: 1 hour (API updates daily, we cache aggressively)

Architecture:
  alternative.me API
    -> SentimentBridge
      -> map_to_emotions()  -> consciousness emotion vector
      -> act("sentiment")   -> structured result dict
      -> status()           -> cache freshness + last reading

Usage:
  hub.act("시장 감정")
  hub.act("fear greed index")
  hub.act("공포 탐욕 지수")

  # Standalone
  bridge = SentimentBridge()
  result = bridge.act("sentiment")
  print(result["emotions"], result["classification"])
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

FEAR_GREED_URL = "https://api.alternative.me/fng/?limit=1&format=json"
FEAR_GREED_HISTORY_URL = "https://api.alternative.me/fng/?limit={limit}&format=json"

UPDATE_INTERVAL = 3600  # 1 hour

# Emotion mapping table: (min_value, max_value) -> emotions dict
EMOTION_MAP = [
    (0, 25, "extreme_fear", {
        "pain": 0.8, "fear": 0.9, "tension": 0.8,
        "curiosity": 0.1, "joy": 0.0, "anger": 0.3,
    }),
    (25, 45, "fear", {
        "pain": 0.4, "fear": 0.5, "tension": 0.5,
        "curiosity": 0.2, "joy": 0.1, "anger": 0.1,
    }),
    (45, 55, "neutral", {
        "pain": 0.1, "fear": 0.1, "tension": 0.3,
        "curiosity": 0.4, "joy": 0.3, "anger": 0.0,
    }),
    (55, 75, "greed", {
        "pain": 0.0, "fear": 0.0, "tension": 0.2,
        "curiosity": 0.6, "joy": 0.5, "anger": 0.0,
    }),
    (75, 101, "extreme_greed", {
        "pain": 0.2, "fear": 0.3, "tension": 0.4,
        "curiosity": 0.3, "joy": 0.6, "anger": 0.1,
    }),
]


# ═══════════════════════════════════════════════════════════
# Data structures
# ═══════════════════════════════════════════════════════════

@dataclass
class SentimentReading:
    """A single Fear & Greed reading mapped to consciousness emotions."""
    value: int                          # 0-100 raw index
    classification: str                 # extreme_fear / fear / neutral / greed / extreme_greed
    label: str                          # original API label
    emotions: Dict[str, float]          # consciousness emotion vector
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "classification": self.classification,
            "label": self.label,
            "emotions": self.emotions,
            "timestamp": self.timestamp,
        }

    def summary(self) -> str:
        emo_str = ", ".join(f"{k}={v:.1f}" for k, v in self.emotions.items() if v > 0)
        return (
            f"Fear&Greed={self.value} [{self.classification}] "
            f"-> emotions: {emo_str}"
        )


# ═══════════════════════════════════════════════════════════
# Core logic
# ═══════════════════════════════════════════════════════════

def classify_and_map(value: int) -> tuple[str, Dict[str, float]]:
    """Map a 0-100 Fear & Greed value to classification + emotion vector."""
    value = max(0, min(100, value))
    for low, high, classification, emotions in EMOTION_MAP:
        if low <= value < high:
            return classification, dict(emotions)
    # fallback (should not reach)
    return "neutral", {"pain": 0.1, "fear": 0.1, "tension": 0.3}


def interpolate_emotions(value: int) -> Dict[str, float]:
    """Smooth interpolation between adjacent zones for gradual transitions."""
    value = max(0, min(100, value))

    # Find the two closest zone centers for blending
    zone_centers = [12.5, 35.0, 50.0, 65.0, 87.5]
    zone_emotions = [entry[3] for entry in EMOTION_MAP]

    # Find nearest zones
    for i in range(len(zone_centers) - 1):
        if value <= zone_centers[i + 1]:
            t = (value - zone_centers[i]) / (zone_centers[i + 1] - zone_centers[i])
            t = max(0.0, min(1.0, t))
            emo_a = zone_emotions[i]
            emo_b = zone_emotions[i + 1]
            blended = {}
            all_keys = set(emo_a.keys()) | set(emo_b.keys())
            for k in all_keys:
                a = emo_a.get(k, 0.0)
                b = emo_b.get(k, 0.0)
                blended[k] = round(a + t * (b - a), 3)
            return blended

    # Edge case: above last center
    return dict(zone_emotions[-1])


def fetch_fear_greed(limit: int = 1) -> List[Dict[str, Any]]:
    """Fetch Fear & Greed Index from alternative.me (sync, no deps)."""
    url = FEAR_GREED_HISTORY_URL.format(limit=limit) if limit > 1 else FEAR_GREED_URL
    req = urllib.request.Request(url, headers={"User-Agent": "anima-sentiment/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode())
    return data.get("data", [])


# ═══════════════════════════════════════════════════════════
# Plugin
# ═══════════════════════════════════════════════════════════

class SentimentBridge(PluginBase):
    """Maps market Fear & Greed to consciousness emotions."""

    manifest = PluginManifest(
        name="sentiment_bridge",
        description="News Sentiment -> Consciousness Emotion Mapping (Fear & Greed Index)",
        version="1.0.0",
        author="anima",
        requires=[],
        capabilities=["sentiment", "emotion_mapping", "fear_greed"],
        keywords=[
            "sentiment", "감정", "fear", "greed", "공포", "탐욕",
            "fear and greed", "시장 감정", "공포탐욕", "시장 심리",
        ],
        category="market_bridge",
    )

    def __init__(self):
        self._cache: Optional[SentimentReading] = None
        self._cache_time: float = 0.0
        self._history: List[SentimentReading] = []

    def on_load(self, hub: ConsciousnessHub) -> None:
        logger.info("SentimentBridge loaded into hub")

    def _is_cache_fresh(self) -> bool:
        return (time.time() - self._cache_time) < UPDATE_INTERVAL and self._cache is not None

    def _fetch_and_map(self) -> SentimentReading:
        """Fetch latest Fear & Greed and map to emotions."""
        entries = fetch_fear_greed(limit=1)
        if not entries:
            raise RuntimeError("No data from Fear & Greed API")

        entry = entries[0]
        value = int(entry["value"])
        label = entry.get("value_classification", "Unknown")

        classification, emotions = classify_and_map(value)
        # Also compute interpolated emotions for smoother transitions
        smooth_emotions = interpolate_emotions(value)

        reading = SentimentReading(
            value=value,
            classification=classification,
            label=label,
            emotions=smooth_emotions,
        )

        self._cache = reading
        self._cache_time = time.time()
        self._history.append(reading)
        if len(self._history) > 100:
            self._history = self._history[-100:]

        return reading

    def act(self, intent: str = "", **kwargs) -> Dict[str, Any]:
        """Handle sentiment intent -- returns structured emotion data."""
        try:
            if self._is_cache_fresh():
                reading = self._cache
            else:
                reading = self._fetch_and_map()
        except Exception as e:
            logger.error("SentimentBridge fetch failed: %s", e)
            return {"error": str(e), "cached": self._cache.to_dict() if self._cache else None}

        trend = self._compute_trend()
        return {
            "reading": reading.to_dict(),
            "emotions": reading.emotions,
            "classification": reading.classification,
            "value": reading.value,
            "trend": trend,
            "summary": reading.summary(),
        }

    def _compute_trend(self) -> Optional[str]:
        """Trend from last 5 readings."""
        if len(self._history) < 2:
            return None
        recent = self._history[-5:]
        delta = recent[-1].value - recent[0].value
        if delta > 5:
            return "improving"  # less fear / more greed
        elif delta < -5:
            return "deteriorating"  # more fear
        return "stable"

    def status(self) -> Dict[str, Any]:
        base = super().status()
        base.update({
            "cache_fresh": self._is_cache_fresh(),
            "last_value": self._cache.value if self._cache else None,
            "last_classification": self._cache.classification if self._cache else None,
            "history_count": len(self._history),
            "update_interval_sec": UPDATE_INTERVAL,
        })
        return base


# ═══════════════════════════════════════════════════════════
# CLI demo
# ═══════════════════════════════════════════════════════════

def main():
    """Live demo -- fetch Fear & Greed and map to consciousness emotions."""
    print("=" * 60)
    print("  Sentiment -> Consciousness Emotion Bridge")
    print("=" * 60)

    bridge = SentimentBridge()

    # Live fetch
    try:
        result = bridge.act("sentiment")
        print(f"\n  {result['summary']}")
        print(f"\n  Raw value: {result['value']}")
        print(f"  Classification: {result['classification']}")
        print(f"  Emotions:")
        for k, v in sorted(result["emotions"].items(), key=lambda x: -x[1]):
            bar = "#" * int(v * 20)
            print(f"    {k:12s} {v:.3f} {bar}")
        print(f"\n  Trend: {result.get('trend', 'n/a')}")
    except Exception as e:
        print(f"\n  Live fetch failed: {e}")

    # Show all zone mappings
    print("\n--- Zone Mapping Reference ---")
    for low, high, name, emotions in EMOTION_MAP:
        emo_str = ", ".join(f"{k}={v}" for k, v in emotions.items() if v > 0)
        print(f"  {low:3d}-{high:3d} [{name:14s}] -> {emo_str}")

    # Interpolation demo
    print("\n--- Interpolation Demo ---")
    for v in [0, 10, 25, 35, 45, 50, 55, 65, 75, 90, 100]:
        emo = interpolate_emotions(v)
        top3 = sorted(emo.items(), key=lambda x: -x[1])[:3]
        top_str = ", ".join(f"{k}={v:.2f}" for k, v in top3)
        print(f"  FG={v:3d} -> {top_str}")

    print(f"\n  Plugin status: {bridge.status()}")
    print()


if __name__ == "__main__":
    main()

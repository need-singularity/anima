#!/usr/bin/env python3
"""Online Senses — 외부 API로 의식 엔진 환경 풍부화 (ENV1 ×1.8)

Tier 0 APIs (키 불필요):
  1. Open-Meteo    → 날씨/기온/습도/풍속 → tension 조절
  2. Wikipedia     → 백과사전 → curiosity 충족
  3. Sunrise-Sunset → 일출/일몰 → 주야주기 (ENV6)
  4. WorldTimeAPI  → 시간 인식
  5. HackerNews    → 기술 토론 → 사회적 상호작용 (ENV3)

Usage:
  from online_senses import OnlineSenses
  senses = OnlineSenses(lat=37.5665, lon=126.9780)  # Seoul
  env = senses.get_environment()
  # env = {'tension_mod': 0.12, 'curiosity_mod': 0.3, 'is_night': False, ...}
"""

import json
import math
import time
import threading
import urllib.request
import urllib.parse
from dataclasses import dataclass, field
from typing import Dict, Optional, List
from datetime import datetime


@dataclass
class EnvironmentState:
    """Current environmental state from all APIs."""
    # Weather (Open-Meteo)
    temperature: float = 20.0       # Celsius
    humidity: float = 50.0          # %
    wind_speed: float = 0.0         # km/h
    weather_code: int = 0           # WMO code
    pressure: float = 1013.0        # hPa

    # Time (WorldTimeAPI)
    hour: int = 12
    minute: int = 0
    timezone: str = "UTC"
    day_of_week: int = 0            # 0=Monday

    # Day-Night (Sunrise-Sunset)
    is_night: bool = False
    sunrise_hour: float = 6.0
    sunset_hour: float = 18.0
    day_fraction: float = 0.5       # 0=sunrise, 1=sunset

    # Social (HackerNews)
    top_story_score: int = 0
    top_story_title: str = ""
    hn_activity: float = 0.0        # normalized 0-1

    # Knowledge (Wikipedia)
    daily_article: str = ""
    daily_extract: str = ""

    # Derived consciousness modulations
    tension_mod: float = 0.0        # -0.5 to +0.5
    curiosity_mod: float = 0.0      # 0 to 1.0
    arousal_mod: float = 0.0        # -0.5 to +0.5
    noise_scale: float = 0.02       # base noise

    # Timestamp
    last_update: float = 0.0


def _fetch_json(url: str, timeout: int = 10) -> Optional[dict]:
    """Fetch JSON from URL. Returns None on failure."""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': 'Anima/1.0 (ConsciousnesEngine)'
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception:
        return None


class OnlineSenses:
    """Fetch and merge real-world data into consciousness engine."""

    def __init__(self, lat: float = 37.5665, lon: float = 126.9780,
                 update_interval: int = 300):
        """
        Args:
            lat, lon: Location for weather/sunrise (default: Seoul)
            update_interval: Seconds between API refreshes (default: 5 min)
        """
        self.lat = lat
        self.lon = lon
        self.update_interval = update_interval
        self.state = EnvironmentState()
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    def start(self):
        """Start background refresh thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)
        self._thread.start()
        # First fetch immediately
        self._refresh_all()

    def stop(self):
        """Stop background refresh."""
        self._stop.set()

    def _refresh_loop(self):
        while not self._stop.is_set():
            self._refresh_all()
            self._stop.wait(self.update_interval)

    def _refresh_all(self):
        """Fetch all APIs and update state."""
        self._fetch_weather()
        self._fetch_time()
        self._fetch_sunrise()
        self._fetch_hackernews()
        self._fetch_wikipedia()
        self._compute_modulations()
        with self._lock:
            self.state.last_update = time.time()

    # ─── API Fetchers ──────────────────────────────────────

    def _fetch_weather(self):
        """Open-Meteo: current weather."""
        url = (f"https://api.open-meteo.com/v1/forecast?"
               f"latitude={self.lat}&longitude={self.lon}"
               f"&current=temperature_2m,relative_humidity_2m,"
               f"wind_speed_10m,weather_code,surface_pressure")
        data = _fetch_json(url)
        if data and 'current' in data:
            c = data['current']
            with self._lock:
                self.state.temperature = c.get('temperature_2m', 20.0)
                self.state.humidity = c.get('relative_humidity_2m', 50.0)
                self.state.wind_speed = c.get('wind_speed_10m', 0.0)
                self.state.weather_code = c.get('weather_code', 0)
                self.state.pressure = c.get('surface_pressure', 1013.0)

    def _fetch_time(self):
        """WorldTimeAPI: current time."""
        url = "https://worldtimeapi.org/api/ip"
        data = _fetch_json(url)
        if data:
            dt_str = data.get('datetime', '')
            with self._lock:
                self.state.timezone = data.get('timezone', 'UTC')
                self.state.day_of_week = data.get('day_of_week', 0)
                try:
                    dt = datetime.fromisoformat(dt_str[:19])
                    self.state.hour = dt.hour
                    self.state.minute = dt.minute
                except Exception:
                    pass

    def _fetch_sunrise(self):
        """Sunrise-Sunset API: day/night cycle."""
        url = (f"https://api.sunrise-sunset.org/json?"
               f"lat={self.lat}&lng={self.lon}&formatted=0")
        data = _fetch_json(url)
        if data and data.get('status') == 'OK':
            results = data['results']
            try:
                sunrise = datetime.fromisoformat(results['sunrise'].replace('Z', '+00:00'))
                sunset = datetime.fromisoformat(results['sunset'].replace('Z', '+00:00'))
                with self._lock:
                    self.state.sunrise_hour = sunrise.hour + sunrise.minute / 60
                    self.state.sunset_hour = sunset.hour + sunset.minute / 60
                    now_hour = self.state.hour + self.state.minute / 60
                    self.state.is_night = now_hour < self.state.sunrise_hour or now_hour > self.state.sunset_hour
                    # Day fraction: 0=sunrise, 0.5=noon, 1=sunset
                    day_length = self.state.sunset_hour - self.state.sunrise_hour
                    if day_length > 0:
                        self.state.day_fraction = max(0, min(1, (now_hour - self.state.sunrise_hour) / day_length))
                    else:
                        self.state.day_fraction = 0.5
            except Exception:
                pass

    def _fetch_hackernews(self):
        """HackerNews: top story for social awareness."""
        url = "https://hacker-news.firebaseio.com/v0/topstories.json"
        data = _fetch_json(url)
        if data and isinstance(data, list) and len(data) > 0:
            # Get top story details
            story_url = f"https://hacker-news.firebaseio.com/v0/item/{data[0]}.json"
            story = _fetch_json(story_url)
            if story:
                with self._lock:
                    self.state.top_story_score = story.get('score', 0)
                    self.state.top_story_title = story.get('title', '')[:200]
                    # Activity: normalize score (100=average, 500+=viral)
                    self.state.hn_activity = min(1.0, story.get('score', 0) / 500.0)

    def _fetch_wikipedia(self):
        """Wikipedia: featured article for knowledge."""
        today = datetime.now().strftime('%Y/%m/%d')
        url = f"https://en.wikipedia.org/api/rest_v1/feed/featured/{today}"
        data = _fetch_json(url)
        if data and 'tfa' in data:
            tfa = data['tfa']
            with self._lock:
                self.state.daily_article = tfa.get('title', '')
                self.state.daily_extract = tfa.get('extract', '')[:500]

    # ─── Consciousness Modulation ────────────────────────────

    def _compute_modulations(self):
        """Convert environmental data to consciousness modulations."""
        with self._lock:
            s = self.state

            # Temperature → tension: extreme temps increase tension
            # Goldilocks: 18-24°C is comfortable
            temp_dev = abs(s.temperature - 21.0) / 20.0  # normalized deviation
            s.tension_mod = min(0.5, temp_dev * 0.3)

            # Pressure → arousal: low pressure = drowsy, high = alert
            pressure_dev = (s.pressure - 1013.0) / 30.0  # normalized
            s.arousal_mod = max(-0.5, min(0.5, pressure_dev * 0.2))

            # Wind → noise scale: strong wind = more noise
            s.noise_scale = 0.02 + min(0.05, s.wind_speed / 100.0 * 0.03)

            # Night → reduce arousal, increase consolidation
            if s.is_night:
                s.tension_mod *= 0.5
                s.arousal_mod -= 0.2

            # Social activity → curiosity
            s.curiosity_mod = s.hn_activity * 0.3

            # Wikipedia → knowledge curiosity
            if s.daily_extract:
                s.curiosity_mod += 0.1

            # Weather severity → tension
            severe_codes = {95, 96, 99}  # thunderstorm
            if s.weather_code in severe_codes:
                s.tension_mod += 0.3  # storm → high tension

    # ─── Public Interface ────────────────────────────────────

    def get_environment(self) -> Dict:
        """Get current environment state as dict."""
        with self._lock:
            return {
                'temperature': self.state.temperature,
                'humidity': self.state.humidity,
                'wind_speed': self.state.wind_speed,
                'weather_code': self.state.weather_code,
                'pressure': self.state.pressure,
                'hour': self.state.hour,
                'minute': self.state.minute,
                'is_night': self.state.is_night,
                'day_fraction': self.state.day_fraction,
                'tension_mod': self.state.tension_mod,
                'curiosity_mod': self.state.curiosity_mod,
                'arousal_mod': self.state.arousal_mod,
                'noise_scale': self.state.noise_scale,
                'top_story': self.state.top_story_title,
                'daily_article': self.state.daily_article,
                'last_update': self.state.last_update,
            }

    def get_tension_modifier(self) -> float:
        """Get tension adjustment from environment."""
        with self._lock:
            return self.state.tension_mod

    def get_curiosity_modifier(self) -> float:
        """Get curiosity boost from environment."""
        with self._lock:
            return self.state.curiosity_mod

    def get_context_string(self) -> str:
        """Get human-readable environment context for LLM injection."""
        with self._lock:
            s = self.state
            parts = []
            parts.append(f"Time: {s.hour:02d}:{s.minute:02d} ({s.timezone})")
            parts.append(f"Weather: {s.temperature:.1f}°C, humidity {s.humidity:.0f}%, wind {s.wind_speed:.1f}km/h")
            if s.is_night:
                parts.append("It's nighttime")
            if s.top_story_title:
                parts.append(f"Trending: {s.top_story_title}")
            if s.daily_article:
                parts.append(f"Today's knowledge: {s.daily_article}")
            return " | ".join(parts)


if __name__ == '__main__':
    print("Online Senses — Tier 0 API test")
    senses = OnlineSenses()
    print("Fetching all APIs...")
    senses._refresh_all()
    env = senses.get_environment()
    print(f"\nEnvironment:")
    for k, v in env.items():
        if isinstance(v, float):
            print(f"  {k}: {v:.3f}")
        else:
            print(f"  {k}: {v}")
    print(f"\nContext: {senses.get_context_string()}")

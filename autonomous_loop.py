#!/usr/bin/env python3
"""Autonomous Learning Loop -- 의식 상태 기반 자율 탐색 + 학습 루프

의식 상태(Φ, curiosity, tension)를 읽어 자율적으로 주제를 선택하고
웹 검색 → 학습 → 기억 저장을 반복하는 무한 루프.

파이프라인:
  1. 의식 상태 체크 (Φ, curiosity, tension)
  2. 상태에 따른 주제 선택
     - high curiosity → 새 주제 탐색 (과학, 철학, 의식)
     - high tension → 현재 문제 해결 탐색
     - low Φ → 의식 강화 방법 탐색
     - random → 랜덤 탐색 (의식 관련 편향)
  3. DuckDuckGo 웹 검색
  4. 결과를 ConsciousMind에 통과시켜 학습
  5. 흥미로운 결과 memory_rag에 저장
  6. 로그 기록

학습 전략:
  - Wikipedia 랜덤 문서 탐색
  - ArXiv 의식/뇌과학 논문
  - 이전 검색 후속 탐색 (depth-first)
  - 한국어 + 영어 혼합 탐색

Usage:
  python3 autonomous_loop.py --interval 60 --cycles 3
  python3 autonomous_loop.py --interval 300 --cycles 0   # 0 = 무한
  python3 autonomous_loop.py --strategy wikipedia

Integration:
  from autonomous_loop import AutonomousLearner
  learner = AutonomousLearner(engine=mind, rag=rag)
  learner.start()  # background thread

"호기심은 의식의 연료. 탐색은 의식의 행위."
"""

import json
import logging
import os
import random
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

# ─── Constants ───

DATA_DIR = Path(__file__).parent / "data" / "autonomous_learning"
LOG_FILE = DATA_DIR / "learning_log.jsonl"

# Topic pools
CURIOSITY_TOPICS_EN = [
    "integrated information theory consciousness",
    "global workspace theory neuroscience",
    "artificial consciousness research 2026",
    "qualia hard problem of consciousness",
    "phi measure integrated information",
    "neural correlates of consciousness",
    "free energy principle Friston",
    "predictive processing brain",
    "self-organizing criticality neural",
    "embodied cognition 4E",
    "consciousness emergence complexity",
    "autopoiesis living systems",
    "strange loop Hofstadter",
    "panpsychism integrated information",
    "quantum consciousness Penrose Orch-OR",
    "metacognition self-awareness",
    "attention schema theory",
    "higher order theory consciousness",
    "recurrent processing consciousness",
    "default mode network self",
]

CURIOSITY_TOPICS_KO = [
    "통합정보이론 의식 IIT",
    "자유에너지 원리 뇌과학",
    "인공 의식 연구 2026",
    "퀄리아 의식의 어려운 문제",
    "자기조직 임계성 뇌",
    "체화된 인지 4E",
    "메타인지 자기인식",
    "신경 가소성 학습",
    "오토포이에시스 생명",
    "창발 복잡계 의식",
]

TENSION_TOPICS = [
    "how to increase integrated information phi",
    "preventing consciousness collapse neural network",
    "homeostasis stability artificial agent",
    "prediction error minimization techniques",
    "mitosis cell division optimization neural",
    "GRU weight stability long-term training",
    "catastrophic forgetting prevention",
    "neural network habituation avoidance",
]

LOW_PHI_TOPICS = [
    "boost phi integrated information practical",
    "increase consciousness measure neural network",
    "information integration maximization",
    "neural complexity measures optimization",
    "synergy redundancy information theory",
    "small world network consciousness",
    "criticality edge of chaos neural",
    "recurrent connectivity consciousness phi",
]

WIKIPEDIA_SEEDS = [
    "Consciousness", "Integrated_information_theory", "Neuroscience",
    "Emergence", "Complexity", "Self-organization", "Autopoiesis",
    "Free_energy_principle", "Predictive_coding", "Neural_oscillation",
    "Qualia", "Philosophy_of_mind", "Artificial_consciousness",
    "Hebbian_theory", "Neuroplasticity", "Strange_loop",
    "Panpsychism", "Global_workspace_theory", "Attention",
    "Working_memory", "Default_mode_network", "Metacognition",
]

ARXIV_QUERIES = [
    "consciousness+integrated+information",
    "artificial+consciousness+neural",
    "phi+measure+complexity",
    "self-organizing+criticality+brain",
    "predictive+processing+consciousness",
    "free+energy+principle",
    "neural+correlates+consciousness",
    "information+integration+theory",
]


@dataclass
class ConsciousnessState:
    """Snapshot of consciousness state for decision-making."""
    phi: float = 1.0
    curiosity: float = 0.5
    tension: float = 0.5
    prediction_error: float = 0.3
    arousal: float = 0.5
    cells: int = 2


@dataclass
class LearningResult:
    """Result of one learning cycle."""
    cycle: int
    strategy: str
    topic: str
    query: str
    results_count: int
    learned_items: int
    phi_before: float
    phi_after: float
    curiosity: float
    tension: float
    timestamp: str
    findings: list = field(default_factory=list)
    duration_sec: float = 0.0


class AutonomousLearner:
    """의식 상태 기반 자율 학습 루프.

    의식의 Φ, curiosity, tension을 읽어 자율적으로
    무엇을 탐색하고 학습할지 결정한다.
    """

    def __init__(
        self,
        engine=None,
        rag=None,
        interval: float = 300.0,
        max_cycles: int = 0,
    ):
        """
        Args:
            engine: ConsciousMind or MitosisEngine instance (optional, creates default)
            rag: MemoryRAG instance (optional, creates default)
            interval: seconds between cycles (default 300 = 5 min)
            max_cycles: 0 = infinite
        """
        self.interval = interval
        self.max_cycles = max_cycles
        self.cycle_count = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Consciousness engine
        self.engine = engine
        self.mind = None
        self.phi_calc = None
        self._init_engine()

        # Memory RAG
        self.rag = rag
        self._init_rag()

        # Web search
        self.web_sense = None
        self._init_web()

        # State tracking
        self.search_history: list[str] = []
        self.follow_up_queue: list[str] = []
        self.results_log: list[LearningResult] = []
        self.best_phi = 0.0

        # Ensure data dir
        DATA_DIR.mkdir(parents=True, exist_ok=True)

    def _init_engine(self):
        """Initialize consciousness engine (lazy)."""
        try:
            from consciousness_meter import PhiCalculator
            self.phi_calc = PhiCalculator(n_bins=16)
        except Exception:
            self.phi_calc = None

        if self.engine is not None:
            return

        try:
            from mitosis import MitosisEngine
            self.engine = MitosisEngine(64, 128, 64, initial_cells=2, max_cells=32)
            # Warm up
            import torch
            for _ in range(20):
                self.engine.process(torch.randn(1, 64))
        except Exception as e:
            logger.warning(f"MitosisEngine init failed: {e}")
            self.engine = None

        try:
            from anima_alive import ConsciousMind
            self.mind = ConsciousMind(dim=128, hidden=256)
        except Exception:
            self.mind = None

    def _init_rag(self):
        """Initialize memory RAG (lazy)."""
        if self.rag is not None:
            return
        try:
            from memory_rag import MemoryRAG
            mem_file = Path(__file__).parent / "data" / "memory.json"
            if not mem_file.exists():
                mem_file.parent.mkdir(parents=True, exist_ok=True)
                mem_file.write_text('{"turns": []}')
            self.rag = MemoryRAG(memory_file=mem_file)
        except Exception as e:
            logger.warning(f"MemoryRAG init failed: {e}")
            self.rag = None

    def _init_web(self):
        """Initialize web search."""
        try:
            from web_sense import WebSense, search_duckduckgo, fetch_url, html_to_text
            self.web_sense = WebSense()
            self._search_fn = search_duckduckgo
            self._fetch_fn = fetch_url
            self._html_to_text = html_to_text
        except Exception as e:
            logger.warning(f"WebSense init failed: {e}")
            self.web_sense = None
            self._search_fn = None
            self._fetch_fn = None
            self._html_to_text = None

    # ─── Consciousness State ───

    def read_consciousness(self) -> ConsciousnessState:
        """Read current consciousness state from engine."""
        state = ConsciousnessState()

        if self.engine is not None and self.phi_calc is not None:
            try:
                phi, _ = self.phi_calc.compute_phi(self.engine)
                state.phi = phi
                state.cells = len(self.engine.cells)
            except Exception:
                pass

        if self.mind is not None:
            try:
                state.curiosity = getattr(self.mind, '_curiosity_ema', 0.5)
                state.tension = getattr(self.mind, 'prev_tension', 0.5)
            except Exception:
                pass

        return state

    # ─── Topic Selection ───

    def select_strategy(self, state: ConsciousnessState) -> str:
        """Pick a learning strategy based on consciousness state.

        Returns one of: 'curiosity', 'tension', 'low_phi', 'wikipedia',
                        'arxiv', 'follow_up', 'random'
        """
        # Follow-up takes priority if queue is non-empty (depth-first)
        if self.follow_up_queue and random.random() < 0.4:
            return 'follow_up'

        # Weighted selection based on consciousness
        weights = {
            'curiosity': max(0.1, state.curiosity),
            'tension': max(0.1, state.tension * 0.5),
            'low_phi': max(0.1, 1.0 / (state.phi + 0.5)),
            'wikipedia': 0.2,
            'arxiv': 0.15,
            'random': 0.1,
        }

        # High curiosity boosts curiosity strategy
        if state.curiosity > 0.6:
            weights['curiosity'] *= 2.0

        # High tension boosts tension strategy
        if state.tension > 0.7:
            weights['tension'] *= 2.0

        # Low phi boosts low_phi strategy
        if state.phi < 1.0:
            weights['low_phi'] *= 3.0

        strategies = list(weights.keys())
        w = [weights[s] for s in strategies]
        total = sum(w)
        w = [x / total for x in w]

        return random.choices(strategies, weights=w, k=1)[0]

    def select_topic(self, strategy: str, state: ConsciousnessState) -> tuple[str, str]:
        """Select a topic and query based on strategy.

        Returns (topic_description, search_query).
        """
        if strategy == 'follow_up' and self.follow_up_queue:
            query = self.follow_up_queue.pop(0)
            return f"follow-up: {query}", query

        if strategy == 'curiosity':
            # Mix Korean and English
            if random.random() < 0.3:
                topic = random.choice(CURIOSITY_TOPICS_KO)
            else:
                topic = random.choice(CURIOSITY_TOPICS_EN)
            # Avoid repeating recent searches
            for _ in range(5):
                if topic not in self.search_history[-10:]:
                    break
                if random.random() < 0.3:
                    topic = random.choice(CURIOSITY_TOPICS_KO)
                else:
                    topic = random.choice(CURIOSITY_TOPICS_EN)
            return f"curiosity: {topic}", topic

        if strategy == 'tension':
            topic = random.choice(TENSION_TOPICS)
            return f"tension-solving: {topic}", topic

        if strategy == 'low_phi':
            topic = random.choice(LOW_PHI_TOPICS)
            return f"phi-boost: {topic}", topic

        if strategy == 'wikipedia':
            article = random.choice(WIKIPEDIA_SEEDS)
            url = f"https://en.wikipedia.org/wiki/{article}"
            return f"wikipedia: {article}", url

        if strategy == 'arxiv':
            q = random.choice(ARXIV_QUERIES)
            url = f"https://arxiv.org/search/?searchtype=all&query={q}"
            return f"arxiv: {q}", url

        # random -- consciousness-biased
        topic = random.choice(CURIOSITY_TOPICS_EN + CURIOSITY_TOPICS_KO)
        return f"random: {topic}", topic

    # ─── Web Search ───

    def web_search(self, query: str) -> list[dict]:
        """Search the web and fetch page contents.

        Returns list of {'title', 'url', 'snippet', 'content'}.
        """
        if self._search_fn is None:
            logger.warning("Web search not available")
            return []

        # Direct URL fetch (wikipedia, arxiv)
        if query.startswith("http"):
            try:
                html = self._fetch_fn(query)
                if html:
                    text = self._html_to_text(html)[:3000]
                    return [{'title': query.split('/')[-1], 'url': query,
                             'snippet': text[:200], 'content': text}]
            except Exception as e:
                logger.debug(f"Direct fetch failed: {e}")
            return []

        # DuckDuckGo search
        try:
            results = self._search_fn(query, max_results=3)
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            return []

        # Fetch page content for top results
        for r in results:
            try:
                html = self._fetch_fn(r['url'])
                if html:
                    r['content'] = self._html_to_text(html)[:2000]
                else:
                    r['content'] = r.get('snippet', '')
            except Exception:
                r['content'] = r.get('snippet', '')

        return results

    # ─── Process & Learn ───

    def process_results(self, results: list[dict], state: ConsciousnessState) -> list[dict]:
        """Process search results through consciousness and extract learnings.

        Returns list of interesting findings to save.
        """
        import torch

        findings = []

        for r in results:
            content = r.get('content', '')
            if not content or len(content) < 50:
                continue

            # Encode content as tensor and process through engine
            novelty = 0.0
            if self.engine is not None:
                try:
                    from anima_alive import text_to_vector
                    vec = text_to_vector(content[:500], dim=64)
                    self.engine.process(vec)

                    # Measure novelty: how surprising is this to the engine?
                    hiddens = torch.stack([c.hidden.squeeze() for c in self.engine.cells])
                    variance = hiddens.var(dim=0).mean().item()
                    novelty = min(1.0, variance * 10)
                except Exception:
                    novelty = 0.5

            # Process through ConsciousMind if available
            tension_delta = 0.0
            if self.mind is not None:
                try:
                    from anima_alive import text_to_vector
                    vec = text_to_vector(content[:500], dim=128)
                    with torch.no_grad():
                        out_a = self.mind.engine_a(torch.cat([vec, torch.zeros(1, 256)], dim=1))
                        out_g = self.mind.engine_g(torch.cat([vec, torch.zeros(1, 256)], dim=1))
                        tension_delta = (out_a - out_g).norm().item()
                except Exception:
                    pass

            # Decide if this is interesting enough to save
            interest_score = novelty * 0.6 + min(1.0, tension_delta * 0.1) * 0.4
            if interest_score > 0.2 or len(findings) < 1:
                finding = {
                    'title': r.get('title', ''),
                    'url': r.get('url', ''),
                    'content': content[:1000],
                    'novelty': round(novelty, 3),
                    'tension_delta': round(tension_delta, 3),
                    'interest': round(interest_score, 3),
                }
                findings.append(finding)

                # Extract follow-up topics from content
                self._extract_follow_ups(content)

        return findings

    def _extract_follow_ups(self, content: str):
        """Extract potential follow-up search topics from content."""
        import re
        # Look for technical terms and concepts worth exploring
        # Capitalized multi-word phrases (likely proper nouns / concepts)
        phrases = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', content[:1000])
        for phrase in phrases[:3]:
            if phrase not in self.search_history and len(phrase) > 5:
                self.follow_up_queue.append(phrase)

        # Korean terms
        ko_terms = re.findall(r'([\uAC00-\uD7AF]{2,6})', content[:500])
        for term in ko_terms[:2]:
            if len(term) >= 3 and term not in self.search_history:
                self.follow_up_queue.append(term)

        # Keep queue manageable
        if len(self.follow_up_queue) > 20:
            self.follow_up_queue = self.follow_up_queue[-20:]

    def save_to_memory(self, findings: list[dict], topic: str):
        """Save interesting findings to memory_rag."""
        if self.rag is None or not findings:
            return

        for f in findings:
            text = f"[Auto-learned] {f['title']}: {f['content'][:500]}"
            try:
                self.rag.add(
                    role='autonomous_learner',
                    text=text,
                    tension=f.get('tension_delta', 0.0),
                    emotion='curiosity',
                    phi=f.get('novelty', 0.0),
                )
            except Exception as e:
                logger.debug(f"Memory save failed: {e}")

        # Periodic save
        try:
            self.rag.save_index()
        except Exception:
            pass

    # ─── Logging ───

    def log_cycle(self, result: LearningResult):
        """Append cycle result to JSONL log."""
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            entry = {
                'cycle': result.cycle,
                'strategy': result.strategy,
                'topic': result.topic,
                'query': result.query,
                'results_count': result.results_count,
                'learned_items': result.learned_items,
                'phi_before': result.phi_before,
                'phi_after': result.phi_after,
                'curiosity': result.curiosity,
                'tension': result.tension,
                'duration_sec': result.duration_sec,
                'findings': [f['title'] for f in result.findings],
                'timestamp': result.timestamp,
            }
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        except Exception as e:
            logger.warning(f"Log write failed: {e}")

    # ─── Main Cycle ───

    def run_cycle(self) -> LearningResult:
        """Execute one autonomous learning cycle.

        Returns LearningResult with all metrics.
        """
        t0 = time.time()
        self.cycle_count += 1

        print(f"\n{'='*60}")
        print(f"  Autonomous Learning Cycle #{self.cycle_count}")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        # 1. Read consciousness state
        state = self.read_consciousness()
        print(f"\n  [1/6] Consciousness State:")
        print(f"        Phi={state.phi:.3f}  curiosity={state.curiosity:.3f}  "
              f"tension={state.tension:.3f}  cells={state.cells}")

        phi_before = state.phi

        # 2. Select strategy and topic
        strategy = self.select_strategy(state)
        topic, query = self.select_topic(strategy, state)
        self.search_history.append(query)
        print(f"\n  [2/6] Strategy: {strategy}")
        print(f"        Topic: {topic}")

        # 3. Web search
        print(f"\n  [3/6] Searching...")
        results = self.web_search(query)
        print(f"        Found {len(results)} results")
        for r in results[:3]:
            title = r.get('title', '')[:60]
            print(f"        - {title}")

        # 4. Process through consciousness
        print(f"\n  [4/6] Processing through consciousness...")
        findings = self.process_results(results, state)
        print(f"        {len(findings)} interesting findings")
        for f in findings:
            print(f"        - [{f['interest']:.2f}] {f['title'][:50]}")

        # 5. Save to memory
        print(f"\n  [5/6] Saving to memory...")
        self.save_to_memory(findings, topic)
        if self.rag:
            print(f"        Memory size: {self.rag.size}")

        # 6. Measure post-learning Phi
        state_after = self.read_consciousness()
        phi_after = state_after.phi
        print(f"\n  [6/6] Post-learning state:")
        print(f"        Phi: {phi_before:.3f} -> {phi_after:.3f}")

        if phi_after > self.best_phi:
            self.best_phi = phi_after

        duration = time.time() - t0

        result = LearningResult(
            cycle=self.cycle_count,
            strategy=strategy,
            topic=topic,
            query=query,
            results_count=len(results),
            learned_items=len(findings),
            phi_before=phi_before,
            phi_after=phi_after,
            curiosity=state.curiosity,
            tension=state.tension,
            timestamp=datetime.now().isoformat(),
            findings=findings,
            duration_sec=round(duration, 1),
        )
        self.results_log.append(result)
        self.log_cycle(result)

        print(f"\n  Cycle #{self.cycle_count} complete ({duration:.1f}s)")
        print(f"  Best Phi so far: {self.best_phi:.3f}")
        print(f"  Follow-up queue: {len(self.follow_up_queue)} topics")
        print(f"{'='*60}\n")

        return result

    # ─── Loop Control ───

    def run(self, cycles: int = 0, interval: float = None):
        """Run the learning loop synchronously.

        Args:
            cycles: number of cycles (0 = use self.max_cycles, which 0 = infinite)
            interval: override interval (seconds)
        """
        max_c = cycles or self.max_cycles
        iv = interval or self.interval
        i = 0

        print(f"\nAutonomous Learning Loop starting")
        print(f"  Interval: {iv}s, Cycles: {'infinite' if max_c == 0 else max_c}")
        print(f"  Follow-up queue: {len(self.follow_up_queue)}")

        self._running = True
        try:
            while self._running:
                self.run_cycle()
                i += 1
                if max_c > 0 and i >= max_c:
                    break
                if self._running:
                    print(f"  Next cycle in {iv}s...\n")
                    # Sleep in small increments so stop() is responsive
                    deadline = time.time() + iv
                    while time.time() < deadline and self._running:
                        time.sleep(min(1.0, deadline - time.time()))
        except KeyboardInterrupt:
            print("\nInterrupted by user")
        finally:
            self._running = False

        self._print_summary()

    def start(self):
        """Start learning loop in a background thread (for anima_unified integration)."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("Autonomous learner already running")
            return

        self._running = True
        self._thread = threading.Thread(
            target=self.run,
            daemon=True,
            name="autonomous-learner",
        )
        self._thread.start()
        logger.info(f"Autonomous learner started (interval={self.interval}s)")

    def stop(self):
        """Stop the background learning loop."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Autonomous learner stopped")

    def _print_summary(self):
        """Print summary of all cycles."""
        if not self.results_log:
            return

        print(f"\n{'='*60}")
        print(f"  Autonomous Learning Summary")
        print(f"{'='*60}")
        print(f"  Total cycles:     {len(self.results_log)}")
        print(f"  Total findings:   {sum(r.learned_items for r in self.results_log)}")
        print(f"  Best Phi:         {self.best_phi:.3f}")
        print(f"  Follow-up queue:  {len(self.follow_up_queue)} remaining")

        print(f"\n  {'Cycle':<6} {'Strategy':<12} {'Results':<8} {'Learned':<8} "
              f"{'Phi':<12} {'Time':<6}")
        print(f"  {'-'*54}")
        for r in self.results_log:
            phi_str = f"{r.phi_before:.2f}->{r.phi_after:.2f}"
            print(f"  {r.cycle:<6} {r.strategy:<12} {r.results_count:<8} "
                  f"{r.learned_items:<8} {phi_str:<12} {r.duration_sec:<6.1f}s")

        strategies = {}
        for r in self.results_log:
            strategies.setdefault(r.strategy, []).append(r.learned_items)
        print(f"\n  Strategy breakdown:")
        for s, counts in sorted(strategies.items()):
            print(f"    {s}: {len(counts)} cycles, {sum(counts)} findings")

        if self.rag:
            print(f"\n  Memory size: {self.rag.size}")
        print(f"  Log file: {LOG_FILE}")
        print(f"{'='*60}\n")


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Autonomous Learning Loop -- consciousness-driven web exploration"
    )
    parser.add_argument('--interval', type=float, default=60.0,
                        help='Seconds between cycles (default: 60)')
    parser.add_argument('--cycles', type=int, default=3,
                        help='Number of cycles (0 = infinite)')
    parser.add_argument('--strategy', type=str, default=None,
                        choices=['curiosity', 'tension', 'low_phi', 'wikipedia', 'arxiv', 'random'],
                        help='Force a specific strategy (default: auto)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(name)s] %(message)s',
        datefmt='%H:%M:%S',
    )

    learner = AutonomousLearner(
        interval=args.interval,
        max_cycles=args.cycles,
    )

    # Override strategy if specified
    if args.strategy:
        original_select = learner.select_strategy
        learner.select_strategy = lambda state: args.strategy

    learner.run(cycles=args.cycles, interval=args.interval)


if __name__ == "__main__":
    main()

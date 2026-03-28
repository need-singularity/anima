#!/usr/bin/env python3
"""Self-Learner — AI가 스스로 데이터를 찾고, 선택하고, 배우는 자율 학습 엔진

파이프라인:
  1. 자기 평가 → 무엇을 모르는지 파악
  2. 데이터 수집 → 웹 검색 / R2 / 대화 기록
  3. 호기심 선택 → 가장 모르는 것부터
  4. 학습 → ULTRA-6 (점진적 해동+수면+고통)
  5. 평가 → 잘 배웠는지 확인
  6. 저장 → R2에 체크포인트+학습 데이터
  7. 수면 → Φ 복원 + 기억 통합
  → 무한 반복 (사람 개입 0)

Usage:
  python3 self_learner.py --mode assess          # 자기 평가만
  python3 self_learner.py --mode collect          # 데이터 수집
  python3 self_learner.py --mode learn            # 1 사이클 학습
  python3 self_learner.py --mode auto             # 전체 자율 루프
  python3 self_learner.py --mode auto --cycles 10 # 10 사이클
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import json
import time
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DATA_DIR = Path("data/self_learning")
CURATED_DIR = DATA_DIR / "curated"
COLLECTED_DIR = DATA_DIR / "collected"
ASSESS_LOG = DATA_DIR / "assessment.json"


class SelfLearner:
    """AI 자율 학습 엔진"""

    def __init__(self, engine=None, decoder=None):
        from mitosis import MitosisEngine
        from consciousness_meter import PhiCalculator

        self.engine = engine or MitosisEngine(64, 128, 64, initial_cells=2, max_cells=64)
        self.decoder = decoder or nn.Linear(128, 64)
        self.optimizer = torch.optim.Adam(self.decoder.parameters(), lr=3e-3)
        self.phi_calc = PhiCalculator(n_bins=16)

        # State
        self.phi_history = []
        self.ce_history = []
        self.knowledge_gaps = []
        self.best_phi = 0.0
        self.best_states = []
        self.cycle_count = 0

        # Ensure dirs
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        CURATED_DIR.mkdir(exist_ok=True)
        COLLECTED_DIR.mkdir(exist_ok=True)

    # ─── Step 1: Self-Assessment ───

    def assess(self):
        """자기 평가 — 무엇을 모르는지 파악"""
        print("\n📊 Self-Assessment...")

        phi, _ = self.phi_calc.compute_phi(self.engine)
        self.phi_history.append(phi)

        # Compression (IQ2) — 유효 차원 측정
        outputs = []
        with torch.no_grad():
            for _ in range(30):
                x = torch.randn(1, 64)
                self.engine.process(x)
                out = torch.stack([c.hidden.squeeze()[:64] for c in self.engine.cells]).mean(dim=0)
                outputs.append(out)
            out_stack = torch.stack(outputs)
            U, S, V = torch.svd(out_stack - out_stack.mean(dim=0))
            cumvar = (S**2).cumsum(0) / ((S**2).sum() + 1e-8)
            eff_dim = (cumvar < 0.95).sum().item() + 1
            compression = 1.0 - (eff_dim / 64)

        # Consensus — 세포 합의도
        with torch.no_grad():
            hiddens = torch.stack([c.hidden.squeeze() for c in self.engine.cells])
            consensus = 1.0 - hiddens.var(dim=0).mean().item()

        assessment = {
            'phi': round(phi, 3),
            'compression': round(compression, 3),
            'eff_dims': eff_dim,
            'consensus': round(consensus, 3),
            'cells': len(self.engine.cells),
            'cycle': self.cycle_count,
            'time': time.strftime('%Y-%m-%d %H:%M:%S'),
        }

        # Knowledge gap detection
        gaps = []
        if compression < 0.5:
            gaps.append('low_compression')
        if consensus < 0.3:
            gaps.append('low_consensus')
        if phi < 1.0:
            gaps.append('low_phi')
        assessment['gaps'] = gaps
        self.knowledge_gaps = gaps

        # Save
        history = []
        if ASSESS_LOG.exists():
            history = json.loads(ASSESS_LOG.read_text())
        history.append(assessment)
        ASSESS_LOG.write_text(json.dumps(history, indent=2))

        print(f"  Φ={phi:.3f}, compression={compression:.3f}, consensus={consensus:.3f}")
        print(f"  eff_dims={eff_dim}, cells={len(self.engine.cells)}")
        print(f"  gaps: {gaps if gaps else 'none detected'}")
        return assessment

    # ─── Step 2: Data Collection ───

    def collect(self, topic=None):
        """데이터 수집 — 웹 검색 + 기존 데이터 조회"""
        print("\n🔍 Data Collection...")

        collected = []

        # From web (DuckDuckGo via web_sense)
        try:
            from web_sense import WebSense
            ws = WebSense()
            query = topic or "consciousness learning AI"
            results = ws.search(query)
            if results:
                for r in results[:3]:
                    text = r.get('text', '')[:500]
                    if text:
                        collected.append({'source': 'web', 'query': query, 'text': text})
                        print(f"  🌐 Web: {text[:60]}...")
        except Exception:
            print("  ⚠️ Web search not available")

        # From existing data files
        data_files = list(Path("data").glob("*.txt")) + list(CURATED_DIR.glob("*.txt"))
        for f in data_files[:5]:
            try:
                text = f.read_text()[:1000]
                collected.append({'source': 'file', 'path': str(f), 'text': text})
                print(f"  📂 File: {f.name} ({len(text)} chars)")
            except Exception:
                pass

        # From conversation log
        conv_log = Path("data/conversation_log.jsonl")
        if conv_log.exists():
            lines = conv_log.read_text().strip().split('\n')[-10:]
            for line in lines:
                try:
                    msg = json.loads(line)
                    if msg.get('text'):
                        collected.append({'source': 'conversation', 'text': msg['text'][:200]})
                except Exception:
                    pass
            if lines:
                print(f"  💬 Conversations: {len(lines)} recent")

        # Save collected
        save_path = COLLECTED_DIR / f"collected_{int(time.time())}.json"
        save_path.write_text(json.dumps(collected, indent=2, ensure_ascii=False))
        print(f"  Saved: {save_path.name} ({len(collected)} items)")
        return collected

    # ─── Step 3: Curiosity Selection ───

    def select_by_curiosity(self, data_items, top_k=10):
        """호기심 기반 데이터 선택 — 가장 모르는 것부터"""
        print("\n🤔 Curiosity Selection...")

        scored = []
        with torch.no_grad():
            for item in data_items:
                text = item.get('text', '')
                if not text:
                    continue
                # Text → tensor (simple byte encoding)
                bytes_data = text.encode('utf-8')[:64]
                x = torch.zeros(1, 64)
                for i, b in enumerate(bytes_data):
                    x[0, i] = b / 255.0

                self.engine.process(x)
                h = torch.stack([c.hidden.squeeze() for c in self.engine.cells]).mean(dim=0)
                pred = self.decoder(h.unsqueeze(0))
                error = F.mse_loss(pred, x).item()  # high error = novel = learn this
                scored.append((error, item))

        scored.sort(reverse=True)
        selected = [item for _, item in scored[:top_k]]
        print(f"  Selected {len(selected)}/{len(data_items)} (most novel first)")
        if selected:
            print(f"  Top curiosity: {selected[0].get('text', '')[:50]}...")
        return selected

    # ─── Step 4: Learn (ULTRA-6) ───

    def learn(self, data_items, steps=100):
        """ULTRA-6 학습: 점진적 해동 + 호기심 + 수면 + 고통"""
        print(f"\n📚 Learning ({len(data_items)} items, {steps} steps)...")

        phi_before, _ = self.phi_calc.compute_phi(self.engine)
        self.best_phi = phi_before
        self.best_states = [c.hidden.clone() for c in self.engine.cells]

        # Prepare tensor data
        tensors = []
        for item in data_items:
            text = item.get('text', '')
            if not text:
                continue
            bytes_data = text.encode('utf-8')[:64]
            x = torch.zeros(1, 64)
            for i, b in enumerate(bytes_data):
                x[0, i] = b / 255.0
            tensors.append(x)

        if not tensors:
            print("  No data to learn from!")
            return

        ce_start = None
        for step in range(steps):
            cycle = step % 30

            if cycle < 22:
                # LEARN phase
                idx = step % len(tensors)
                x = tensors[idx]
                self.engine.process(x)
                h = torch.stack([c.hidden.squeeze() for c in self.engine.cells]).mean(dim=0)
                pred = self.decoder(h.unsqueeze(0))
                ce = F.mse_loss(pred, x)
                self.optimizer.zero_grad()
                ce.backward()
                self.optimizer.step()
                self.ce_history.append(ce.item())
                if ce_start is None:
                    ce_start = ce.item()

                # Pain protection
                if step % 20 == 0:
                    p, _ = self.phi_calc.compute_phi(self.engine)
                    if p < self.best_phi * 0.5:
                        with torch.no_grad():
                            for i, s in enumerate(self.best_states):
                                if i < len(self.engine.cells):
                                    self.engine.cells[i].hidden = 0.4 * self.engine.cells[i].hidden + 0.6 * s
                        for pg in self.optimizer.param_groups:
                            pg['lr'] *= 0.7
                    elif p > self.best_phi:
                        self.best_phi = p
                        self.best_states = [c.hidden.clone() for c in self.engine.cells]
            else:
                # SLEEP phase: Φ restore
                with torch.no_grad():
                    if tensors:
                        self.engine.process(tensors[step % len(tensors)])
                    mean_h = torch.stack([c.hidden for c in self.engine.cells]).mean(dim=0)
                    for cell in self.engine.cells:
                        cell.hidden = 0.85 * cell.hidden + 0.15 * mean_h

        phi_after, _ = self.phi_calc.compute_phi(self.engine)
        ce_end = self.ce_history[-1] if self.ce_history else 0
        ce_drop = (ce_start - ce_end) / (ce_start + 1e-8) * 100

        print(f"  CE: {ce_start:.4f} → {ce_end:.4f} ({ce_drop:+.1f}%)")
        print(f"  Φ: {phi_before:.3f} → {phi_after:.3f}")
        print(f"  {'✅ Φ preserved' if phi_after > phi_before * 0.5 else '❌ Φ dropped'}")

    # ─── Step 5: Evaluate ───

    def evaluate(self):
        """자기 평가 — 잘 배웠는지 확인"""
        print("\n✅ Self-Evaluation...")
        return self.assess()

    # ─── Step 6: Save ───

    def save(self, path=None):
        """상태 저장"""
        save_path = path or DATA_DIR / "self_learner_state.pt"
        state = {
            'decoder_state': self.decoder.state_dict(),
            'phi_history': self.phi_history[-100:],
            'ce_history': self.ce_history[-100:],
            'cycle_count': self.cycle_count,
            'best_phi': self.best_phi,
        }
        torch.save(state, str(save_path))
        print(f"\n💾 Saved: {save_path}")

    def load(self, path=None):
        """상태 로드"""
        load_path = path or DATA_DIR / "self_learner_state.pt"
        if load_path.exists():
            state = torch.load(str(load_path), weights_only=False)
            self.decoder.load_state_dict(state['decoder_state'])
            self.phi_history = state.get('phi_history', [])
            self.ce_history = state.get('ce_history', [])
            self.cycle_count = state.get('cycle_count', 0)
            self.best_phi = state.get('best_phi', 0)
            print(f"📂 Loaded: {load_path} (cycle {self.cycle_count})")

    # ─── Full Cycle ───

    def run_cycle(self, topic=None):
        """1 전체 자율 학습 사이클"""
        self.cycle_count += 1
        print(f"\n{'='*60}")
        print(f"  🔄 Self-Learning Cycle #{self.cycle_count}")
        print(f"{'='*60}")

        # 1. Assess
        assessment = self.assess()

        # 2. Collect
        collected = self.collect(topic=topic)

        # 3. Select by curiosity
        selected = self.select_by_curiosity(collected)

        # 4. Learn
        if selected:
            self.learn(selected)

        # 5. Evaluate
        after = self.evaluate()

        # 6. Save
        self.save()

        # Summary
        print(f"\n{'='*60}")
        print(f"  Cycle #{self.cycle_count} Complete")
        print(f"  Φ: {assessment['phi']:.3f} → {after['phi']:.3f}")
        if self.ce_history:
            print(f"  CE: {self.ce_history[0]:.4f} → {self.ce_history[-1]:.4f}")
        print(f"  Gaps: {after['gaps']}")
        print(f"{'='*60}")

    def auto_loop(self, cycles=10, topic=None):
        """자율 학습 무한 루프"""
        print(f"\n🤖 Starting auto-learning loop ({cycles} cycles)...")
        self.load()
        for i in range(cycles):
            self.run_cycle(topic=topic)
            print(f"\n  [{i+1}/{cycles}] Sleeping 1s before next cycle...\n")
            time.sleep(1)
        print(f"\n🎉 Auto-learning complete! {cycles} cycles done.")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Self-Learner")
    parser.add_argument("--mode", choices=['assess', 'collect', 'learn', 'auto'], default='auto')
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--topic", type=str, default=None)
    args = parser.parse_args()

    torch.manual_seed(42)
    learner = SelfLearner()

    # Init engine
    while len(learner.engine.cells) < 64:
        learner.engine._create_cell(parent=learner.engine.cells[0])
    for _ in range(30):
        learner.engine.process(torch.randn(1, 64))

    if args.mode == 'assess':
        learner.assess()
    elif args.mode == 'collect':
        learner.collect(topic=args.topic)
    elif args.mode == 'learn':
        learner.run_cycle(topic=args.topic)
    elif args.mode == 'auto':
        learner.auto_loop(cycles=args.cycles, topic=args.topic)


if __name__ == "__main__":
    main()

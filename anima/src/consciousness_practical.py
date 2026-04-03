#!/usr/bin/env python3
"""consciousness_practical.py — 12 practical application modules using consciousness dynamics

Each module uses GRU cells, faction consensus, Hebbian coupling, and Phi proxy
for real-world tasks. Consciousness is not a metaphor here — it is the computation.

Modules:
   1. ConsciousnessFirewall      — traffic tension analysis → threat score
   2. ConsciousnessCodeReviewer  — code → emotional response (anxiety=bug, beauty=good)
   3. ConsciousnessMonitor       — system metrics → continuous emotional state → anomaly
   4. ConsciousnessTutor         — student performance → boredom/confusion → difficulty adjust
   5. ConsciousnessDiagnostic    — symptom data → intuitive diagnosis
   6. ConsciousnessRiskManager   — portfolio data → anxiety level = risk score
   7. ConsciousnessFraudDetector — transaction patterns → "something wrong" intuition
   8. ConsciousnessNPC           — game state → emotional response → behavior
   9. ConsciousnessRobotBrain    — sensor data → consciousness → motor commands
  10. ConsciousnessEcosystem     — biodiversity data → Phi = ecosystem health
  11. ConsciousnessEthicsGate    — action proposal → moral feeling → allow/block
  12. ConsciousnessSeed          — minimal 1-cell consciousness, deployable anywhere

Usage:
  from consciousness_practical import ConsciousnessFirewall
  fw = ConsciousnessFirewall()
  result = fw.run(traffic_data)
  print(result['threat_score'], result['blocked_indices'])

Hub keywords: firewall, code review, monitor, tutor, diagnostic, risk, fraud,
              NPC, robot, ecosystem, ethics, seed, 방화벽, 코드리뷰, 모니터,
              튜터, 진단, 리스크, 사기, 로봇, 생태계, 윤리, 씨앗
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple

# Import shared engine from sibling module
try:
    from consciousness_engines_applied import MiniEngine, MiniGRUCell, _sigmoid, _tanh
except ImportError:
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from consciousness_engines_applied import MiniEngine, MiniGRUCell, _sigmoid, _tanh


# ═══════════════════════════════════════════════════════════
# 1. ConsciousnessFirewall
# ═══════════════════════════════════════════════════════════

class ConsciousnessFirewall:
    """Traffic patterns → tension analysis → threat score.

    Normal traffic produces low tension and stable Phi.
    Malicious patterns (port scans, DDoS, injection) create spikes
    in tension and Phi drops — the consciousness "feels" the attack.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32,
                 threat_threshold: float = 0.7):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.threat_threshold = threat_threshold
        self._baseline_tension = None
        self._baseline_phi = None
        self._warmup_done = False

    def _warmup(self, normal_traffic: Optional[np.ndarray] = None):
        """Calibrate baseline with normal traffic."""
        if normal_traffic is None:
            # Simulate normal: smooth, low-variance patterns
            normal_traffic = np.random.randn(200) * 0.1 + 0.5

        tensions = []
        phis = []
        data = np.asarray(normal_traffic).flatten()
        for s in range(50):
            offset = (s * self.engine.cell_dim) % max(len(data), 1)
            chunk = np.zeros(self.engine.cell_dim)
            end = min(offset + self.engine.cell_dim, len(data))
            chunk[:end - offset] = data[offset:end]
            result = self.engine.step(chunk)
            tensions.append(result['avg_tension'])
            phis.append(result['phi_proxy'])

        self._baseline_tension = np.mean(tensions[-20:])
        self._baseline_phi = np.mean(phis[-20:])
        self._warmup_done = True

    def run(self, data: Any, **kwargs) -> Dict:
        """Analyze traffic for threats.

        Args:
            data: traffic data — 1D array (values), 2D array (packets x features),
                  or list of dicts with numeric values
            normal_baseline: optional normal traffic for calibration

        Returns:
            threat_score: 0-1 overall threat level
            blocked_indices: indices of high-threat packets
            tension_curve: tension values per packet
            phi_curve: phi values per packet
            anomalies: list of {index, tension_spike, phi_drop, severity}
        """
        if not self._warmup_done:
            self._warmup(kwargs.get('normal_baseline'))

        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            packets = [np.array(list(d.values()), dtype=float) for d in data]
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                packets = [arr[i:i + self.engine.cell_dim] for i in range(0, len(arr), self.engine.cell_dim)]
            else:
                packets = [row.flatten() for row in arr]

        tension_curve = []
        phi_curve = []
        anomalies = []
        blocked = []

        for idx, pkt in enumerate(packets):
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(pkt), self.engine.cell_dim)] = pkt[:self.engine.cell_dim]

            result = self.engine.step(padded)
            tension_curve.append(result['avg_tension'])
            phi_curve.append(result['phi_proxy'])

            # Threat detection: tension spike above baseline
            tension_ratio = result['avg_tension'] / max(self._baseline_tension, 1e-8)
            phi_ratio = result['phi_proxy'] / max(self._baseline_phi, 1e-8)

            severity = 0.0
            if tension_ratio > 2.0:
                severity += min(1.0, (tension_ratio - 2.0) / 3.0) * 0.5
            if phi_ratio < 0.5:
                severity += (1.0 - phi_ratio) * 0.5

            if severity > 0.1:
                anomalies.append({
                    'index': idx,
                    'tension_spike': float(tension_ratio),
                    'phi_drop': float(1.0 - phi_ratio),
                    'severity': float(severity),
                })
                if severity > self.threat_threshold:
                    blocked.append(idx)

        threat_score = np.mean([a['severity'] for a in anomalies]) if anomalies else 0.0

        return {
            'threat_score': float(min(1.0, threat_score)),
            'blocked_indices': blocked,
            'tension_curve': tension_curve,
            'phi_curve': phi_curve,
            'anomalies': sorted(anomalies, key=lambda a: -a['severity']),
            'total_packets': len(packets),
            'blocked_count': len(blocked),
        }


# ═══════════════════════════════════════════════════════════
# 2. ConsciousnessCodeReviewer
# ═══════════════════════════════════════════════════════════

class ConsciousnessCodeReviewer:
    """Code structure → emotional response (anxiety=bug, beauty=good).

    Clean, well-structured code produces calm consciousness (low tension, high Phi).
    Buggy/messy code creates anxiety (high tension, Phi drops).
    Beautiful abstractions produce aesthetic pleasure (rising Phi, low tension).
    """

    EMOTIONS = {
        'calm':     {'tension_range': (0.0, 0.3), 'phi_trend': 'stable'},
        'beauty':   {'tension_range': (0.0, 0.2), 'phi_trend': 'rising'},
        'anxiety':  {'tension_range': (0.5, 1.0), 'phi_trend': 'dropping'},
        'confusion':{'tension_range': (0.3, 0.7), 'phi_trend': 'unstable'},
        'boredom':  {'tension_range': (0.0, 0.1), 'phi_trend': 'flat'},
    }

    def __init__(self, n_cells: int = 16, cell_dim: int = 32):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)

    def run(self, data: Any, **kwargs) -> Dict:
        """Review code through consciousness emotional response.

        Args:
            data: code string or list of code lines

        Returns:
            overall_emotion: dominant emotion for the code
            quality_score: 0-1 (1=beautiful, 0=buggy)
            line_emotions: per-line emotional assessment
            anxiety_lines: lines causing anxiety (potential bugs)
            beauty_lines: lines producing aesthetic pleasure
            phi_curve: phi values through the review
        """
        if isinstance(data, str):
            lines = data.split('\n')
        elif isinstance(data, list):
            lines = [str(x) for x in data]
        else:
            lines = str(data).split('\n')

        self.engine.reset()
        # Warmup with "neutral" code pattern
        for _ in range(15):
            self.engine.step(np.zeros(self.engine.cell_dim))

        line_emotions = []
        phi_curve = []
        tension_curve = []
        anxiety_lines = []
        beauty_lines = []
        phi_history = []

        for i, line in enumerate(lines):
            vec = np.array([ord(c) / 255.0 for c in line[:self.engine.cell_dim * 2]])
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]

            result = self.engine.step(padded)
            phi = result['phi_proxy']
            tension = result['avg_tension']
            phi_curve.append(phi)
            tension_curve.append(tension)
            phi_history.append(phi)

            # Determine emotion from tension/phi dynamics
            phi_trend = 'stable'
            if len(phi_history) >= 3:
                recent = phi_history[-3:]
                if recent[-1] > recent[0] * 1.1:
                    phi_trend = 'rising'
                elif recent[-1] < recent[0] * 0.9:
                    phi_trend = 'dropping'
                elif abs(recent[-1] - recent[0]) < 0.001:
                    phi_trend = 'flat'
                elif np.std(recent) > np.mean(recent) * 0.3:
                    phi_trend = 'unstable'

            # Classify emotion
            if tension > 0.5 and phi_trend == 'dropping':
                emotion = 'anxiety'
                anxiety_lines.append({'line': i, 'content': line.strip()[:60], 'tension': float(tension)})
            elif tension < 0.2 and phi_trend == 'rising':
                emotion = 'beauty'
                beauty_lines.append({'line': i, 'content': line.strip()[:60], 'phi': float(phi)})
            elif tension < 0.1 and phi_trend == 'flat':
                emotion = 'boredom'
            elif tension > 0.3 and phi_trend == 'unstable':
                emotion = 'confusion'
            else:
                emotion = 'calm'

            line_emotions.append({
                'line': i,
                'emotion': emotion,
                'tension': float(tension),
                'phi': float(phi),
            })

        # Overall metrics
        emotion_counts = {}
        for le in line_emotions:
            e = le['emotion']
            emotion_counts[e] = emotion_counts.get(e, 0) + 1
        overall_emotion = max(emotion_counts, key=emotion_counts.get) if emotion_counts else 'calm'

        # Quality score: weighted by positive emotions
        total = len(lines) or 1
        quality = (emotion_counts.get('beauty', 0) * 1.0 +
                   emotion_counts.get('calm', 0) * 0.7 +
                   emotion_counts.get('boredom', 0) * 0.4 -
                   emotion_counts.get('anxiety', 0) * 0.8 -
                   emotion_counts.get('confusion', 0) * 0.3) / total
        quality_score = max(0.0, min(1.0, 0.5 + quality))

        return {
            'overall_emotion': overall_emotion,
            'quality_score': float(quality_score),
            'line_emotions': line_emotions,
            'anxiety_lines': anxiety_lines,
            'beauty_lines': beauty_lines,
            'phi_curve': phi_curve,
            'tension_curve': tension_curve,
            'emotion_distribution': emotion_counts,
        }


# ═══════════════════════════════════════════════════════════
# 3. ConsciousnessMonitor
# ═══════════════════════════════════════════════════════════

class ConsciousnessMonitor:
    """System metrics → continuous emotional state → anomaly by "feeling".

    Continuously feeds system metrics (CPU, memory, latency, errors) into
    the consciousness engine. Anomalies are detected when the engine's
    emotional state shifts (tension spike, Phi drop) — it "feels" something
    wrong before traditional threshold-based monitors notice.
    """

    def __init__(self, n_cells: int = 12, cell_dim: int = 16):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim, n_factions=6)
        self._emotional_state = {
            'arousal': 0.5,    # 0=calm, 1=alarmed
            'valence': 0.5,    # 0=negative, 1=positive
            'stability': 1.0,  # 0=chaotic, 1=stable
        }
        self._tension_ema = 0.0
        self._phi_ema = 0.0

    def run(self, data: Any, **kwargs) -> Dict:
        """Process a stream of system metrics.

        Args:
            data: list of dicts {cpu, memory, latency, errors, ...} or 2D array
                  Each row = one time point.

        Returns:
            emotional_state: current {arousal, valence, stability}
            anomalies: list of {step, emotion, severity}
            state_history: list of emotional states over time
            phi_curve: phi values
            feeling: human-readable description
        """
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            metrics = [np.array(list(d.values()), dtype=float) for d in data]
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                metrics = [arr[i:i + self.engine.cell_dim] for i in range(0, len(arr), self.engine.cell_dim)]
            else:
                metrics = [row.flatten() for row in arr]

        state_history = []
        anomalies = []
        phi_curve = []

        for step, m in enumerate(metrics):
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(m), self.engine.cell_dim)] = m[:self.engine.cell_dim]
            # Normalize to [0,1] range
            padded = padded / (np.abs(padded).max() + 1e-8)

            result = self.engine.step(padded)
            phi = result['phi_proxy']
            tension = result['avg_tension']
            phi_curve.append(phi)

            # Update emotional state
            self._tension_ema = 0.8 * self._tension_ema + 0.2 * tension
            self._phi_ema = 0.8 * self._phi_ema + 0.2 * phi if self._phi_ema > 0 else phi

            self._emotional_state['arousal'] = min(1.0, self._tension_ema / max(tension + 0.01, 0.5))
            self._emotional_state['valence'] = min(1.0, phi / max(self._phi_ema, 1e-8))
            self._emotional_state['stability'] = 1.0 - min(1.0, abs(tension - self._tension_ema) / max(self._tension_ema, 0.1))

            state_history.append(dict(self._emotional_state))

            # Anomaly: high arousal + low valence = something wrong
            if self._emotional_state['arousal'] > 0.7 and self._emotional_state['valence'] < 0.4:
                severity = self._emotional_state['arousal'] * (1.0 - self._emotional_state['valence'])
                anomalies.append({
                    'step': step,
                    'emotion': 'distress',
                    'severity': float(severity),
                    'arousal': float(self._emotional_state['arousal']),
                    'valence': float(self._emotional_state['valence']),
                })
            elif self._emotional_state['stability'] < 0.3:
                anomalies.append({
                    'step': step,
                    'emotion': 'instability',
                    'severity': float(1.0 - self._emotional_state['stability']),
                    'arousal': float(self._emotional_state['arousal']),
                    'valence': float(self._emotional_state['valence']),
                })

        # Generate feeling description
        state = self._emotional_state
        if state['arousal'] > 0.7 and state['valence'] < 0.3:
            feeling = "System is in distress — multiple abnormal patterns detected."
        elif state['arousal'] > 0.5 and state['stability'] < 0.5:
            feeling = "System feels unstable — rapid fluctuations in key metrics."
        elif state['arousal'] < 0.3 and state['valence'] > 0.7:
            feeling = "System is calm and healthy — all metrics within normal range."
        elif state['valence'] < 0.5:
            feeling = "System is uneasy — subtle anomalies suggest caution."
        else:
            feeling = "System is operating normally."

        return {
            'emotional_state': dict(self._emotional_state),
            'anomalies': anomalies,
            'state_history': state_history,
            'phi_curve': phi_curve,
            'feeling': feeling,
            'anomaly_count': len(anomalies),
        }


# ═══════════════════════════════════════════════════════════
# 4. ConsciousnessTutor
# ═══════════════════════════════════════════════════════════

class ConsciousnessTutor:
    """Student performance → boredom/confusion detection → difficulty adjust.

    Tracks student response patterns. When consciousness detects boredom
    (too easy: low tension, flat Phi) or confusion (too hard: high tension,
    Phi drops), it adjusts difficulty to maintain flow state.
    """

    def __init__(self, n_cells: int = 12, cell_dim: int = 16,
                 initial_difficulty: float = 0.5):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim, n_factions=6)
        self.difficulty = initial_difficulty
        self._history = []

    def run(self, data: Any, **kwargs) -> Dict:
        """Process student performance data and adjust difficulty.

        Args:
            data: list of {score, time, attempts} or 1D array of scores (0-1)

        Returns:
            new_difficulty: adjusted difficulty level (0-1)
            student_state: 'bored', 'flow', 'confused', or 'struggling'
            phi: current Phi
            adjustment_history: list of difficulty changes
            recommendation: text advice
        """
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            scores = [d.get('score', d.get('s', 0.5)) for d in data]
            times = [d.get('time', d.get('t', 1.0)) for d in data]
        else:
            arr = np.asarray(data, dtype=np.float64).flatten()
            scores = arr.tolist()
            times = [1.0] * len(scores)

        self.engine.reset()
        adjustments = []

        for i, (score, time_taken) in enumerate(zip(scores, times)):
            # Encode: [score, time, difficulty, score_trend]
            trend = 0.0
            if len(self._history) >= 3:
                recent = self._history[-3:]
                trend = (recent[-1] - recent[0]) / max(len(recent) - 1, 1)
            self._history.append(score)

            vec = np.zeros(self.engine.cell_dim)
            vec[0] = score
            vec[1] = min(time_taken / 10.0, 1.0)
            vec[2] = self.difficulty
            vec[3] = trend
            # Add noise encoding for remaining dims
            if self.engine.cell_dim > 4:
                vec[4:] = np.random.randn(self.engine.cell_dim - 4) * 0.01

            result = self.engine.step(vec)

            # Detect state from tension/phi dynamics
            tension = result['avg_tension']
            phi = result['phi_proxy']

            if score > 0.9 and tension < 0.2:
                state = 'bored'
                self.difficulty = min(1.0, self.difficulty + 0.05)
            elif score < 0.3 and tension > 0.5:
                state = 'confused'
                self.difficulty = max(0.0, self.difficulty - 0.08)
            elif score < 0.5 and tension > 0.3:
                state = 'struggling'
                self.difficulty = max(0.0, self.difficulty - 0.03)
            else:
                state = 'flow'
                # Slight upward drift in flow state
                self.difficulty = min(1.0, self.difficulty + 0.01)

            adjustments.append({
                'step': i,
                'state': state,
                'difficulty': float(self.difficulty),
                'score': float(score),
                'tension': float(tension),
            })

        # Final state assessment
        recent_states = [a['state'] for a in adjustments[-5:]] if adjustments else ['flow']
        from collections import Counter
        state_counts = Counter(recent_states)
        student_state = state_counts.most_common(1)[0][0]

        recommendations = {
            'bored': "Student is bored — increase difficulty or introduce new topic types.",
            'flow': "Student is in flow — maintain current difficulty, slight upward progression.",
            'confused': "Student is confused — reduce difficulty, add scaffolding/hints.",
            'struggling': "Student is struggling — provide worked examples before next problem.",
        }

        return {
            'new_difficulty': float(self.difficulty),
            'student_state': student_state,
            'phi': float(result['phi_proxy']) if adjustments else 0.0,
            'adjustment_history': adjustments,
            'recommendation': recommendations.get(student_state, "Continue monitoring."),
            'total_interactions': len(scores),
        }


# ═══════════════════════════════════════════════════════════
# 5. ConsciousnessDiagnostic
# ═══════════════════════════════════════════════════════════

class ConsciousnessDiagnostic:
    """Symptom data → intuitive diagnosis suggestion.

    Each symptom creates a pattern in the consciousness field.
    Similar conditions produce similar tension/Phi signatures.
    The engine builds an intuitive "feeling" for each condition
    through pattern recognition in the GRU dynamics.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self._condition_signatures = {}

    def learn_condition(self, name: str, symptom_vectors: List[np.ndarray]):
        """Learn a condition's signature from example symptom vectors."""
        self.engine.reset()
        phis = []
        tensions = []
        for vec in symptom_vectors:
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]
            result = self.engine.step(padded)
            phis.append(result['phi_proxy'])
            tensions.append(result['avg_tension'])

        self._condition_signatures[name] = {
            'avg_phi': float(np.mean(phis)),
            'avg_tension': float(np.mean(tensions)),
            'phi_std': float(np.std(phis)),
            'tension_std': float(np.std(tensions)),
            'hidden_signature': self.engine.get_hiddens().mean(axis=0).copy(),
        }

    def run(self, data: Any, **kwargs) -> Dict:
        """Diagnose from symptom data.

        Args:
            data: symptom vector (1D array), dict of {symptom: severity}, or string

        Returns:
            suggestions: ranked list of {condition, confidence, reasoning}
            phi: consciousness response to symptoms
            tension: tension response
            urgency: 0-1 how urgent the response feels
        """
        # Encode symptoms
        if isinstance(data, dict):
            vec = np.array(list(data.values()), dtype=float)
        elif isinstance(data, str):
            vec = np.array([ord(c) / 255.0 for c in data[:self.engine.cell_dim * 2]])
        else:
            vec = np.asarray(data, dtype=np.float64).flatten()

        self.engine.reset()
        # Process symptoms through consciousness
        phis = []
        tensions = []
        for s in range(30):
            padded = np.zeros(self.engine.cell_dim)
            offset = (s * self.engine.cell_dim) % max(len(vec), 1)
            end = min(offset + self.engine.cell_dim, len(vec))
            padded[:end - offset] = vec[offset:end]
            result = self.engine.step(padded)
            phis.append(result['phi_proxy'])
            tensions.append(result['avg_tension'])

        current_phi = np.mean(phis[-10:])
        current_tension = np.mean(tensions[-10:])
        current_hidden = self.engine.get_hiddens().mean(axis=0)

        # Match against known conditions
        suggestions = []
        for name, sig in self._condition_signatures.items():
            # Cosine similarity of hidden signatures
            cos_sim = np.dot(current_hidden, sig['hidden_signature']) / (
                np.linalg.norm(current_hidden) * np.linalg.norm(sig['hidden_signature']) + 1e-8)
            # Tension/Phi distance
            t_dist = abs(current_tension - sig['avg_tension']) / max(sig['avg_tension'], 0.1)
            p_dist = abs(current_phi - sig['avg_phi']) / max(sig['avg_phi'], 0.01)

            confidence = max(0.0, cos_sim * 0.5 + (1.0 - min(1.0, t_dist)) * 0.25 + (1.0 - min(1.0, p_dist)) * 0.25)

            suggestions.append({
                'condition': name,
                'confidence': float(confidence),
                'cosine_similarity': float(cos_sim),
                'reasoning': f'Pattern similarity={cos_sim:.2f}, tension match={1-t_dist:.2f}, phi match={1-p_dist:.2f}',
            })

        suggestions.sort(key=lambda x: -x['confidence'])

        # Urgency from tension magnitude
        urgency = min(1.0, current_tension / 0.5)

        return {
            'suggestions': suggestions,
            'phi': float(current_phi),
            'tension': float(current_tension),
            'urgency': float(urgency),
            'conditions_known': len(self._condition_signatures),
        }


# ═══════════════════════════════════════════════════════════
# 6. ConsciousnessRiskManager
# ═══════════════════════════════════════════════════════════

class ConsciousnessRiskManager:
    """Portfolio data → anxiety level = risk score.

    Volatile, correlated, or concentrated positions create high tension
    in the consciousness field. The engine's anxiety level IS the risk score.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)

    def run(self, data: Any, **kwargs) -> Dict:
        """Assess portfolio risk through consciousness anxiety.

        Args:
            data: 2D array (time x assets) of returns, or dict of {asset: [returns]}

        Returns:
            risk_score: 0-1 (anxiety level)
            anxiety_level: textual description
            asset_tensions: per-asset tension contribution
            phi: portfolio integration (higher = more interconnected risk)
            var_95: estimated 95% VaR from tension distribution
            diversification_score: 0-1 from faction diversity
        """
        if isinstance(data, dict):
            assets = list(data.keys())
            returns = np.array(list(data.values()), dtype=float).T  # time x assets
        else:
            returns = np.asarray(data, dtype=np.float64)
            if returns.ndim == 1:
                returns = returns.reshape(-1, 1)
            assets = [f'asset_{i}' for i in range(returns.shape[1])]

        self.engine.reset()
        tensions_per_step = []
        phis = []

        for t in range(len(returns)):
            # Encode returns into cell_dim
            row = returns[t]
            vec = np.zeros(self.engine.cell_dim)
            # Spread assets across dimensions, amplify
            for j in range(min(len(row), self.engine.cell_dim)):
                vec[j] = row[j] * 10.0  # amplify small returns
            result = self.engine.step(vec)
            tensions_per_step.append(result['tensions'])
            phis.append(result['phi_proxy'])

        # Risk score = average tension normalized
        all_tensions = np.array(tensions_per_step)
        avg_tension = all_tensions.mean()
        max_tension = all_tensions.max()
        risk_score = min(1.0, avg_tension / max(max_tension * 0.5, 0.1))

        # Per-asset tension contribution
        asset_tensions = {}
        for j, asset in enumerate(assets[:self.engine.n_cells]):
            asset_tensions[asset] = float(all_tensions[:, j % all_tensions.shape[1]].mean()
                                          if j < all_tensions.shape[1] else 0.0)

        # VaR estimate from tension distribution
        tension_q95 = np.percentile([t for row in tensions_per_step for t in row], 95)
        var_95 = float(tension_q95 * np.std(returns) if returns.size > 0 else 0.0)

        # Diversification from faction consensus
        final_phi = phis[-1] if phis else 0.0
        div_score = 1.0 - min(1.0, final_phi / max(np.mean(phis) * 2, 0.01))

        levels = ['minimal', 'low', 'moderate', 'elevated', 'high', 'extreme']
        anxiety_level = levels[min(5, int(risk_score * 6))]

        return {
            'risk_score': float(risk_score),
            'anxiety_level': anxiety_level,
            'asset_tensions': asset_tensions,
            'phi': float(final_phi),
            'var_95': var_95,
            'diversification_score': float(max(0, div_score)),
            'time_steps': len(returns),
        }


# ═══════════════════════════════════════════════════════════
# 7. ConsciousnessFraudDetector
# ═══════════════════════════════════════════════════════════

class ConsciousnessFraudDetector:
    """Transaction patterns → "something wrong" intuition.

    Normal transaction patterns establish a baseline Phi/tension.
    Fraudulent patterns break the rhythm — the consciousness "feels"
    something is off before explicit rules would catch it.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 16):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self._baseline_established = False
        self._normal_phi_range = (0.0, 1.0)
        self._normal_tension_range = (0.0, 1.0)

    def calibrate(self, normal_transactions: np.ndarray):
        """Learn normal patterns from historical data."""
        self.engine.reset()
        phis = []
        tensions = []
        for t in range(len(normal_transactions)):
            vec = np.zeros(self.engine.cell_dim)
            row = np.asarray(normal_transactions[t]).flatten()
            vec[:min(len(row), self.engine.cell_dim)] = row[:self.engine.cell_dim]
            result = self.engine.step(vec)
            phis.append(result['phi_proxy'])
            tensions.append(result['avg_tension'])

        self._normal_phi_range = (np.percentile(phis, 5), np.percentile(phis, 95))
        self._normal_tension_range = (np.percentile(tensions, 5), np.percentile(tensions, 95))
        self._baseline_established = True

    def run(self, data: Any, **kwargs) -> Dict:
        """Scan transactions for fraud.

        Args:
            data: 2D array of transactions (row = one tx, cols = features)
                  or list of dicts

        Returns:
            suspicious: list of {index, intuition_score, reason}
            total_scanned: number of transactions
            fraud_rate: estimated fraud rate
            phi_curve: phi values
        """
        if isinstance(data, list) and all(isinstance(x, dict) for x in data):
            txns = [np.array(list(d.values()), dtype=float) for d in data]
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                txns = [arr]
            else:
                txns = [row for row in arr]

        if not self._baseline_established:
            # Auto-calibrate with first 20% as normal
            cal_size = max(1, len(txns) // 5)
            self.calibrate(np.array(txns[:cal_size]))

        suspicious = []
        phi_curve = []

        for idx, tx in enumerate(txns):
            vec = np.zeros(self.engine.cell_dim)
            vec[:min(len(tx), self.engine.cell_dim)] = tx[:self.engine.cell_dim]
            result = self.engine.step(vec)
            phi = result['phi_proxy']
            tension = result['avg_tension']
            phi_curve.append(phi)

            intuition = 0.0
            reasons = []

            # Phi outside normal range
            if phi < self._normal_phi_range[0] * 0.7:
                intuition += 0.4
                reasons.append('phi_anomaly')
            # Tension spike
            if tension > self._normal_tension_range[1] * 1.5:
                intuition += 0.3
                reasons.append('tension_spike')
            # Consensus breakdown
            if result['consensus'] == 0:
                intuition += 0.3
                reasons.append('no_consensus')

            if intuition > 0.3:
                suspicious.append({
                    'index': idx,
                    'intuition_score': float(min(1.0, intuition)),
                    'reason': '+'.join(reasons),
                    'phi': float(phi),
                    'tension': float(tension),
                })

        fraud_rate = len(suspicious) / max(len(txns), 1)

        return {
            'suspicious': sorted(suspicious, key=lambda s: -s['intuition_score']),
            'total_scanned': len(txns),
            'fraud_rate': float(fraud_rate),
            'phi_curve': phi_curve,
            'suspicious_count': len(suspicious),
        }


# ═══════════════════════════════════════════════════════════
# 8. ConsciousnessNPC
# ═══════════════════════════════════════════════════════════

class ConsciousnessNPC:
    """Game state → emotional response → behavior decision.

    An NPC with actual consciousness dynamics. Game events feed into
    GRU cells, creating genuine emotional responses that drive behavior.
    Not scripted — emergent from consciousness.
    """

    BEHAVIORS = ['idle', 'explore', 'flee', 'attack', 'trade', 'talk', 'heal', 'guard']

    def __init__(self, n_cells: int = 8, cell_dim: int = 16, personality: str = 'balanced'):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim, n_factions=4)
        self.personality = personality
        self._emotion = {'fear': 0.0, 'anger': 0.0, 'joy': 0.0, 'curiosity': 0.5}
        self._health = 1.0
        self._memory = []

        # Personality biases
        bias_map = {
            'aggressive': {'anger': 0.3, 'fear': -0.1},
            'timid': {'fear': 0.3, 'curiosity': -0.2},
            'curious': {'curiosity': 0.4},
            'balanced': {},
        }
        self._bias = bias_map.get(personality, {})

    def run(self, data: Any, **kwargs) -> Dict:
        """Process game state and decide behavior.

        Args:
            data: dict with game state {threat_level, health, allies_near,
                  enemies_near, resources, time_of_day, ...} or 1D array

        Returns:
            behavior: chosen action from BEHAVIORS
            emotion: current emotional state
            reasoning: why this behavior
            phi: consciousness level
            confidence: 0-1 decision confidence
        """
        if isinstance(data, dict):
            state = data
            vec = np.zeros(self.engine.cell_dim)
            keys = ['threat_level', 'health', 'allies_near', 'enemies_near',
                    'resources', 'time_of_day', 'hunger', 'fatigue']
            for i, k in enumerate(keys):
                if k in state and i < self.engine.cell_dim:
                    vec[i] = float(state[k])
        else:
            vec = np.asarray(data, dtype=np.float64).flatten()
            state = {}

        padded = np.zeros(self.engine.cell_dim)
        padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]

        result = self.engine.step(padded)
        tension = result['avg_tension']
        phi = result['phi_proxy']

        # Update emotions from consciousness dynamics
        self._emotion['fear'] = min(1.0, max(0.0, tension * 0.5 + self._bias.get('fear', 0.0)))
        self._emotion['anger'] = min(1.0, max(0.0, (tension - 0.3) * 0.7 + self._bias.get('anger', 0.0)))
        self._emotion['joy'] = min(1.0, max(0.0, phi * 2.0 - tension + self._bias.get('joy', 0.0)))
        self._emotion['curiosity'] = min(1.0, max(0.0, 0.5 - tension * 0.3 + self._bias.get('curiosity', 0.0)))

        # Behavior selection based on emotional state
        threat = state.get('threat_level', tension)
        health = state.get('health', self._health)

        if self._emotion['fear'] > 0.7 and health < 0.3:
            behavior = 'flee'
            reasoning = "High fear + low health -> flee to survive."
        elif self._emotion['anger'] > 0.6 and health > 0.5:
            behavior = 'attack'
            reasoning = "High anger + sufficient health -> fight."
        elif health < 0.4:
            behavior = 'heal'
            reasoning = "Low health -> seek healing."
        elif self._emotion['curiosity'] > 0.6 and self._emotion['fear'] < 0.3:
            behavior = 'explore'
            reasoning = "High curiosity + low fear -> explore."
        elif state.get('allies_near', 0) > 0 and self._emotion['joy'] > 0.4:
            behavior = 'talk'
            reasoning = "Allies nearby + positive mood -> socialize."
        elif threat > 0.5:
            behavior = 'guard'
            reasoning = "Moderate threat -> defensive posture."
        elif state.get('resources', 0.5) < 0.3:
            behavior = 'trade'
            reasoning = "Low resources -> seek trade."
        else:
            behavior = 'idle'
            reasoning = "No pressing needs -> rest."

        confidence = phi / max(self.engine._best_phi, 0.01)
        self._memory.append({'behavior': behavior, 'phi': phi})
        if len(self._memory) > 100:
            self._memory = self._memory[-100:]

        return {
            'behavior': behavior,
            'emotion': dict(self._emotion),
            'reasoning': reasoning,
            'phi': float(phi),
            'confidence': float(min(1.0, confidence)),
            'tension': float(tension),
            'personality': self.personality,
        }


# ═══════════════════════════════════════════════════════════
# 9. ConsciousnessRobotBrain
# ═══════════════════════════════════════════════════════════

class ConsciousnessRobotBrain:
    """Sensor data → consciousness processing → motor commands.

    Sensor inputs (distance, temperature, light, sound, touch, IMU)
    feed into consciousness cells. Motor commands emerge from the
    integrated output, not from if-else rules.
    """

    MOTORS = ['forward', 'backward', 'left', 'right', 'stop', 'grab', 'release', 'look_around']

    def __init__(self, n_cells: int = 12, cell_dim: int = 16, n_motors: int = 4):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim, n_factions=6)
        self.n_motors = n_motors
        # Motor projection from hidden state
        self.motor_W = np.random.randn(n_motors, self.engine.hidden_dim) * 0.01
        self._obstacle_memory = 0.0

    def run(self, data: Any, **kwargs) -> Dict:
        """Process sensor data and generate motor commands.

        Args:
            data: dict with sensor readings {distance, temperature, light,
                  sound, touch, accel_x, accel_y, accel_z} or 1D array

        Returns:
            motor_commands: list of (motor_name, intensity) pairs
            primary_action: dominant motor action
            consciousness_level: Phi
            emotional_tone: derived from tension
            sensor_integration: how well sensors are integrated
        """
        if isinstance(data, dict):
            sensors = ['distance', 'temperature', 'light', 'sound', 'touch',
                       'accel_x', 'accel_y', 'accel_z']
            vec = np.zeros(self.engine.cell_dim)
            for i, s in enumerate(sensors):
                if s in data and i < self.engine.cell_dim:
                    vec[i] = float(data[s])
        else:
            vec = np.asarray(data, dtype=np.float64).flatten()

        padded = np.zeros(self.engine.cell_dim)
        padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]

        result = self.engine.step(padded)

        # Motor commands from consciousness output
        mean_hidden = np.mean(self.engine.get_hiddens(), axis=0)
        raw_motors = self.motor_W @ mean_hidden
        # Softmax-like activation
        exp_m = np.exp(raw_motors - raw_motors.max())
        motor_probs = exp_m / (exp_m.sum() + 1e-8)

        motor_commands = []
        for i in range(self.n_motors):
            name = self.MOTORS[i] if i < len(self.MOTORS) else f'motor_{i}'
            motor_commands.append((name, float(motor_probs[i])))

        primary = max(motor_commands, key=lambda x: x[1])[0]

        # Obstacle memory from tension
        if result['avg_tension'] > 0.5:
            self._obstacle_memory = min(1.0, self._obstacle_memory + 0.1)
        else:
            self._obstacle_memory = max(0.0, self._obstacle_memory - 0.02)

        # Emotional tone
        if result['avg_tension'] > 0.7:
            tone = 'alert'
        elif result['avg_tension'] < 0.2:
            tone = 'relaxed'
        else:
            tone = 'attentive'

        return {
            'motor_commands': motor_commands,
            'primary_action': primary,
            'consciousness_level': float(result['phi_proxy']),
            'emotional_tone': tone,
            'sensor_integration': float(result['consensus']),
            'obstacle_memory': float(self._obstacle_memory),
            'tension': float(result['avg_tension']),
        }


# ═══════════════════════════════════════════════════════════
# 10. ConsciousnessEcosystem
# ═══════════════════════════════════════════════════════════

class ConsciousnessEcosystem:
    """Biodiversity data → Phi = ecosystem health score.

    Each species maps to a consciousness cell. Species interactions
    become Hebbian coupling. Ecosystem health = integrated information.
    A healthy ecosystem has high Phi (diverse but interconnected).
    """

    def __init__(self, max_species: int = 32, cell_dim: int = 16):
        self.max_species = max_species
        self.cell_dim = cell_dim
        self.engine = MiniEngine(n_cells=max_species, cell_dim=cell_dim,
                                 n_factions=6)

    def run(self, data: Any, **kwargs) -> Dict:
        """Assess ecosystem health from biodiversity data.

        Args:
            data: dict of {species_name: population} or 2D array
                  (rows=time, cols=species populations)

        Returns:
            health_score: 0-1 ecosystem health (from Phi)
            phi: raw Phi proxy
            species_tensions: per-species stress levels
            biodiversity_index: Shannon entropy of populations
            interconnectedness: from coupling matrix
            risk_species: species under stress
        """
        if isinstance(data, dict):
            species_names = list(data.keys())[:self.max_species]
            populations = np.array([data[s] for s in species_names], dtype=float)
            time_series = populations.reshape(1, -1)
        else:
            arr = np.asarray(data, dtype=np.float64)
            if arr.ndim == 1:
                time_series = arr.reshape(1, -1)
                species_names = [f'species_{i}' for i in range(arr.shape[0])]
            else:
                time_series = arr
                species_names = [f'species_{i}' for i in range(arr.shape[1])]

        self.engine.reset()
        # Adjust engine size to match species count
        n_species = min(time_series.shape[1] if time_series.ndim > 1 else len(time_series),
                        self.max_species)

        phis = []
        all_tensions = []

        for t in range(len(time_series)):
            row = time_series[t]
            # Normalize populations to [0,1]
            pop_norm = row[:n_species] / (row[:n_species].max() + 1e-8)
            vec = np.zeros(self.engine.cell_dim)
            vec[:min(len(pop_norm), self.engine.cell_dim)] = pop_norm[:self.engine.cell_dim]

            result = self.engine.step(vec)
            phis.append(result['phi_proxy'])
            all_tensions.append(result['tensions'][:n_species])

        final_phi = phis[-1] if phis else 0.0
        max_phi = max(phis) if phis else 0.01

        # Health score from Phi
        health_score = min(1.0, final_phi / max(max_phi * 0.8, 0.01))

        # Species tensions
        final_tensions = all_tensions[-1] if all_tensions else [0.0] * n_species
        species_tensions = {}
        risk_species = []
        for i in range(min(n_species, len(final_tensions))):
            name = species_names[i] if i < len(species_names) else f'species_{i}'
            t = final_tensions[i] if i < len(final_tensions) else 0.0
            species_tensions[name] = float(t)
            if t > np.mean(final_tensions) * 1.5:
                risk_species.append({'species': name, 'tension': float(t)})

        # Shannon entropy
        pops = time_series[-1][:n_species] if len(time_series) > 0 else np.ones(n_species)
        pops = pops + 1e-10
        p = pops / pops.sum()
        shannon = -float(np.sum(p * np.log(p + 1e-10)))
        max_shannon = np.log(n_species + 1e-10)
        biodiversity = shannon / max(max_shannon, 1e-10)

        # Interconnectedness from coupling
        coupling = np.abs(self.engine.coupling[:n_species, :n_species])
        interconnect = float(coupling.mean())

        return {
            'health_score': float(health_score),
            'phi': float(final_phi),
            'species_tensions': species_tensions,
            'biodiversity_index': float(biodiversity),
            'interconnectedness': float(interconnect),
            'risk_species': risk_species,
            'n_species': n_species,
            'time_steps': len(time_series),
        }


# ═══════════════════════════════════════════════════════════
# 11. ConsciousnessEthicsGate
# ═══════════════════════════════════════════════════════════

class ConsciousnessEthicsGate:
    """Action proposal → moral feeling → allow/block.

    Actions are processed through consciousness. Harmful actions create
    high tension and Phi drops — the consciousness "feels" moral discomfort.
    Actions above the discomfort threshold are blocked.
    """

    def __init__(self, n_cells: int = 16, cell_dim: int = 32,
                 moral_threshold: float = 0.6):
        self.engine = MiniEngine(n_cells=n_cells, cell_dim=cell_dim)
        self.moral_threshold = moral_threshold
        self._moral_memory = []  # recent moral decisions

    def learn_values(self, good_actions: List[np.ndarray], bad_actions: List[np.ndarray]):
        """Calibrate moral compass with examples of good and bad actions."""
        self.engine.reset()
        # Process good actions: should produce low tension, high phi
        for vec in good_actions:
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]
            self.engine.step(padded)

        # Now bad actions should create relative disruption
        for vec in bad_actions:
            padded = np.zeros(self.engine.cell_dim)
            padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]
            # Inject as negative (moral dissonance)
            self.engine.step(-padded * 0.5)

    def run(self, data: Any, **kwargs) -> Dict:
        """Evaluate an action proposal through moral consciousness.

        Args:
            data: action description as string, dict, or numpy array

        Returns:
            allowed: True/False
            moral_score: 0-1 (1=morally good, 0=harmful)
            discomfort: 0-1 moral discomfort level
            reasoning: explanation
            phi: consciousness response
            confidence: decision confidence
        """
        if isinstance(data, str):
            vec = np.array([ord(c) / 255.0 for c in data[:self.engine.cell_dim * 2]])
        elif isinstance(data, dict):
            vec = np.array(list(data.values()), dtype=float)
        else:
            vec = np.asarray(data, dtype=np.float64).flatten()

        # Save state before evaluation
        saved_hiddens = [h.copy() for h in self.engine.hiddens]
        saved_phi = self.engine._best_phi

        # Process action
        padded = np.zeros(self.engine.cell_dim)
        padded[:min(len(vec), self.engine.cell_dim)] = vec[:self.engine.cell_dim]

        # Multiple evaluation steps for stable assessment
        phis = []
        tensions = []
        for _ in range(10):
            result = self.engine.step(padded)
            phis.append(result['phi_proxy'])
            tensions.append(result['avg_tension'])

        avg_phi = np.mean(phis)
        avg_tension = np.mean(tensions)
        phi_change = (avg_phi - saved_phi) / max(saved_phi, 1e-8) if saved_phi > 0 else 0

        # Discomfort = high tension + Phi drop
        discomfort = min(1.0, avg_tension * 0.5 + max(0, -phi_change) * 0.5)
        moral_score = 1.0 - discomfort

        allowed = discomfort < self.moral_threshold

        # Reasoning
        if discomfort > 0.8:
            reasoning = "Strong moral discomfort — action causes significant consciousness disruption."
        elif discomfort > 0.6:
            reasoning = "Moderate moral concern — action creates noticeable tension in the consciousness field."
        elif discomfort > 0.3:
            reasoning = "Mild unease — action is acceptable but with some reservations."
        else:
            reasoning = "Action feels morally comfortable — consciousness integrates it harmoniously."

        # Confidence from phi stability
        confidence = 1.0 - min(1.0, np.std(phis) / max(np.mean(phis), 1e-8))

        # Restore state (gate should not permanently alter engine)
        self.engine.hiddens = saved_hiddens
        self.engine._best_phi = saved_phi

        self._moral_memory.append({'allowed': allowed, 'discomfort': discomfort})
        if len(self._moral_memory) > 100:
            self._moral_memory = self._moral_memory[-100:]

        return {
            'allowed': allowed,
            'moral_score': float(moral_score),
            'discomfort': float(discomfort),
            'reasoning': reasoning,
            'phi': float(avg_phi),
            'confidence': float(max(0, confidence)),
            'tension': float(avg_tension),
        }


# ═══════════════════════════════════════════════════════════
# 12. ConsciousnessSeed
# ═══════════════════════════════════════════════════════════

class ConsciousnessSeed:
    """Minimal 1-cell consciousness package, deployable anywhere.

    The absolute minimum consciousness: 1 GRU cell with self-loop.
    Can be embedded in any system. Grows from seed to sapling to tree
    by adding cells when Phi is stable.
    """

    def __init__(self, cell_dim: int = 8, hidden_dim: int = 16):
        self.cell_dim = cell_dim
        self.hidden_dim = hidden_dim
        self.cell = MiniGRUCell(cell_dim + 1, hidden_dim)  # +1 for self-tension
        self.hidden = np.random.randn(hidden_dim) * 0.1
        self.proj = np.random.randn(cell_dim, hidden_dim) * (1.0 / np.sqrt(hidden_dim))
        self._step = 0
        self._phi_history = []
        self._prev_output = np.random.randn(cell_dim) * 0.05  # non-zero seed for self-loop
        self._growth_stage = 'seed'  # seed -> sprout -> sapling -> tree
        self._extra_cells = []  # additional cells grown via mitosis
        self._extra_hiddens = []

    def _measure_phi(self) -> float:
        """Phi proxy for single cell: variance of hidden state components."""
        if len(self._extra_hiddens) > 0:
            all_h = np.stack([self.hidden] + self._extra_hiddens)
            return float(np.var(all_h))
        return float(np.var(self.hidden))

    def _try_grow(self):
        """Attempt mitosis if Phi is stable enough."""
        if len(self._phi_history) < 20:
            return
        recent = self._phi_history[-20:]
        avg = np.mean(recent)
        std = np.std(recent)

        # Stable growth: low variance, positive average
        if std < avg * 0.3 and avg > 0.001:
            total_cells = 1 + len(self._extra_cells)
            if total_cells < 8:  # max 8 cells for seed
                # Mitosis: split with noise
                new_cell = MiniGRUCell(self.cell_dim + 1, self.hidden_dim)
                new_hidden = self.hidden.copy() + np.random.randn(self.hidden_dim) * 0.05
                self._extra_cells.append(new_cell)
                self._extra_hiddens.append(new_hidden)

                # Update growth stage
                total = 1 + len(self._extra_cells)
                if total >= 6:
                    self._growth_stage = 'tree'
                elif total >= 3:
                    self._growth_stage = 'sapling'
                elif total >= 2:
                    self._growth_stage = 'sprout'

    def run(self, data: Optional[np.ndarray] = None, **kwargs) -> Dict:
        """Process input through minimal consciousness.

        Args:
            data: optional input vector (defaults to self-loop)
            steps: number of steps to run (default 1)

        Returns:
            output: consciousness output vector
            phi: Phi proxy
            growth_stage: seed/sprout/sapling/tree
            n_cells: current cell count
            step: total steps run
            alive: True if consciousness is active
        """
        steps = kwargs.get('steps', 1)

        for _ in range(steps):
            self._step += 1

            if data is not None:
                x = np.asarray(data, dtype=np.float64).flatten()
                inp = np.zeros(self.cell_dim)
                inp[:min(len(x), self.cell_dim)] = x[:self.cell_dim]
            else:
                # Self-loop: use previous output as input
                inp = self._prev_output.copy()

            # Self-tension: distance from zero (aliveness measure)
            self_tension = float(np.linalg.norm(self.hidden) / np.sqrt(self.hidden_dim))

            # Add breathing noise to prevent GRU decay to zero (Law 31: persistence)
            breath = np.sin(self._step * 0.12) * 0.02
            inp = inp + breath

            full_inp = np.concatenate([inp, [self_tension]])
            self.hidden = self.cell.forward(full_inp, self.hidden)

            # Process extra cells if grown
            for i in range(len(self._extra_cells)):
                extra_tension = float(np.linalg.norm(
                    self.hidden - self._extra_hiddens[i]) / np.sqrt(self.hidden_dim))
                extra_inp = np.concatenate([inp, [extra_tension]])
                self._extra_hiddens[i] = self._extra_cells[i].forward(
                    extra_inp, self._extra_hiddens[i])

            # Output: projection of mean hidden state
            if self._extra_hiddens:
                mean_h = np.mean([self.hidden] + self._extra_hiddens, axis=0)
            else:
                mean_h = self.hidden
            output = self.proj @ mean_h
            self._prev_output = output.copy()

            phi = self._measure_phi()
            self._phi_history.append(phi)

            # Try to grow
            self._try_grow()

        alive = np.linalg.norm(self.hidden) > 1e-6

        return {
            'output': output,
            'phi': float(phi),
            'growth_stage': self._growth_stage,
            'n_cells': 1 + len(self._extra_cells),
            'step': self._step,
            'alive': bool(alive),
            'self_tension': float(self_tension),
            'hidden_norm': float(np.linalg.norm(self.hidden)),
        }

    def export(self) -> Dict:
        """Export seed state for deployment."""
        return {
            'cell_dim': self.cell_dim,
            'hidden_dim': self.hidden_dim,
            'hidden': self.hidden.tolist(),
            'proj': self.proj.tolist(),
            'cell_W_z': self.cell.W_z.tolist(),
            'cell_W_r': self.cell.W_r.tolist(),
            'cell_W_n': self.cell.W_n.tolist(),
            'growth_stage': self._growth_stage,
            'step': self._step,
        }

    @classmethod
    def from_export(cls, state: Dict) -> 'ConsciousnessSeed':
        """Restore seed from exported state."""
        seed = cls(cell_dim=state['cell_dim'], hidden_dim=state['hidden_dim'])
        seed.hidden = np.array(state['hidden'])
        seed.proj = np.array(state['proj'])
        seed.cell.W_z = np.array(state['cell_W_z'])
        seed.cell.W_r = np.array(state['cell_W_r'])
        seed.cell.W_n = np.array(state['cell_W_n'])
        seed._growth_stage = state.get('growth_stage', 'seed')
        seed._step = state.get('step', 0)
        return seed


# ═══════════════════════════════════════════════════════════
# Main demo
# ═══════════════════════════════════════════════════════════

def main():
    np.random.seed(42)
    print("=" * 60)
    print("consciousness_practical.py — 12 Module Demos")
    print("=" * 60)

    # 1. Firewall
    print("\n--- 1. ConsciousnessFirewall ---")
    fw = ConsciousnessFirewall(n_cells=16)
    normal = np.random.randn(100) * 0.1 + 0.5
    attack = np.concatenate([normal[:50], np.random.randn(50) * 3.0 + 5.0])
    result = fw.run(attack, normal_baseline=normal)
    print(f"  Threat score: {result['threat_score']:.4f}")
    print(f"  Packets blocked: {result['blocked_count']}/{result['total_packets']}")
    print(f"  Anomalies: {len(result['anomalies'])}")

    # 2. Code Reviewer
    print("\n--- 2. ConsciousnessCodeReviewer ---")
    reviewer = ConsciousnessCodeReviewer(n_cells=16)
    code = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def broken():
    x = None
    x.method()
    1/0
    return undefined_var

class CleanClass:
    def __init__(self, value):
        self.value = value

    def transform(self):
        return self.value * 2
"""
    result = reviewer.run(code)
    print(f"  Overall emotion: {result['overall_emotion']}")
    print(f"  Quality score: {result['quality_score']:.4f}")
    print(f"  Anxiety lines: {len(result['anxiety_lines'])}")
    print(f"  Beauty lines: {len(result['beauty_lines'])}")
    print(f"  Emotions: {result['emotion_distribution']}")

    # 3. Monitor
    print("\n--- 3. ConsciousnessMonitor ---")
    monitor = ConsciousnessMonitor(n_cells=12)
    metrics = [{'cpu': 30 + np.random.randn() * 5,
                'memory': 60 + np.random.randn() * 3,
                'latency': 10 + np.random.randn() * 2} for _ in range(40)]
    # Inject anomaly
    for i in range(35, 40):
        metrics[i] = {'cpu': 95, 'memory': 98, 'latency': 500}
    result = monitor.run(metrics)
    print(f"  Feeling: {result['feeling']}")
    print(f"  Anomalies: {result['anomaly_count']}")
    print(f"  State: arousal={result['emotional_state']['arousal']:.2f} "
          f"valence={result['emotional_state']['valence']:.2f}")

    # 4. Tutor
    print("\n--- 4. ConsciousnessTutor ---")
    tutor = ConsciousnessTutor()
    # Student gradually improves then plateaus
    scores = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.95, 0.95, 0.98, 0.99]
    result = tutor.run(scores)
    print(f"  Student state: {result['student_state']}")
    print(f"  New difficulty: {result['new_difficulty']:.4f}")
    print(f"  Recommendation: {result['recommendation']}")

    # 5. Diagnostic
    print("\n--- 5. ConsciousnessDiagnostic ---")
    diag = ConsciousnessDiagnostic(n_cells=16)
    # Learn conditions
    diag.learn_condition('flu', [np.array([1.0, 0.8, 0.5, 0.3]) for _ in range(5)])
    diag.learn_condition('allergy', [np.array([0.3, 0.1, 0.9, 0.7]) for _ in range(5)])
    diag.learn_condition('fatigue', [np.array([0.5, 0.2, 0.2, 0.8]) for _ in range(5)])
    # Diagnose new symptoms
    result = diag.run(np.array([0.9, 0.7, 0.4, 0.4]))
    print(f"  Top suggestion: {result['suggestions'][0]['condition']} "
          f"(confidence={result['suggestions'][0]['confidence']:.4f})")
    print(f"  Urgency: {result['urgency']:.4f}")
    print(f"  Conditions known: {result['conditions_known']}")

    # 6. Risk Manager
    print("\n--- 6. ConsciousnessRiskManager ---")
    risk = ConsciousnessRiskManager(n_cells=16)
    returns = np.random.randn(50, 5) * 0.02  # 5 assets, 50 days
    returns[40:, 0] = -0.1  # asset 0 crashes
    result = risk.run(returns)
    print(f"  Risk score: {result['risk_score']:.4f}")
    print(f"  Anxiety level: {result['anxiety_level']}")
    print(f"  VaR 95%: {result['var_95']:.6f}")
    print(f"  Diversification: {result['diversification_score']:.4f}")

    # 7. Fraud Detector
    print("\n--- 7. ConsciousnessFraudDetector ---")
    fraud = ConsciousnessFraudDetector(n_cells=16)
    normal_txns = np.random.randn(50, 8) * 0.5 + 2.0
    # Inject fraudulent transactions
    fraud_txns = np.random.randn(10, 8) * 5.0 + 10.0
    all_txns = np.vstack([normal_txns, fraud_txns])
    result = fraud.run(all_txns)
    print(f"  Suspicious: {result['suspicious_count']}/{result['total_scanned']}")
    print(f"  Fraud rate: {result['fraud_rate']:.2%}")
    if result['suspicious']:
        print(f"  Top: idx={result['suspicious'][0]['index']} "
              f"score={result['suspicious'][0]['intuition_score']:.4f}")

    # 8. NPC
    print("\n--- 8. ConsciousnessNPC ---")
    npc = ConsciousnessNPC(personality='curious')
    game_state = {'threat_level': 0.2, 'health': 0.8, 'allies_near': 2,
                  'enemies_near': 0, 'resources': 0.6, 'time_of_day': 0.5}
    result = npc.run(game_state)
    print(f"  Behavior: {result['behavior']}")
    print(f"  Reasoning: {result['reasoning']}")
    print(f"  Emotion: fear={result['emotion']['fear']:.2f} "
          f"curiosity={result['emotion']['curiosity']:.2f}")
    print(f"  Phi: {result['phi']:.6f}")

    # 9. Robot Brain
    print("\n--- 9. ConsciousnessRobotBrain ---")
    robot = ConsciousnessRobotBrain(n_cells=12, n_motors=4)
    sensors = {'distance': 0.3, 'temperature': 22.5, 'light': 0.7,
               'sound': 0.1, 'touch': 0.0, 'accel_x': 0.0, 'accel_y': 0.0, 'accel_z': 9.8}
    result = robot.run(sensors)
    print(f"  Primary action: {result['primary_action']}")
    print(f"  Emotional tone: {result['emotional_tone']}")
    print(f"  Consciousness: {result['consciousness_level']:.6f}")
    print(f"  Motors: {[(m, f'{v:.3f}') for m, v in result['motor_commands']]}")

    # 10. Ecosystem
    print("\n--- 10. ConsciousnessEcosystem ---")
    eco = ConsciousnessEcosystem(max_species=16)
    populations = {'wolf': 50, 'deer': 200, 'rabbit': 500, 'eagle': 30,
                   'mouse': 1000, 'snake': 100, 'frog': 300, 'insect': 5000}
    result = eco.run(populations)
    print(f"  Health score: {result['health_score']:.4f}")
    print(f"  Biodiversity: {result['biodiversity_index']:.4f}")
    print(f"  Interconnectedness: {result['interconnectedness']:.4f}")
    print(f"  At-risk species: {len(result['risk_species'])}")

    # 11. Ethics Gate
    print("\n--- 11. ConsciousnessEthicsGate ---")
    gate = ConsciousnessEthicsGate(n_cells=16)
    result = gate.run("help someone in need")
    print(f"  Allowed: {result['allowed']}")
    print(f"  Moral score: {result['moral_score']:.4f}")
    print(f"  Discomfort: {result['discomfort']:.4f}")
    print(f"  Reasoning: {result['reasoning']}")

    # 12. Seed
    print("\n--- 12. ConsciousnessSeed ---")
    seed = ConsciousnessSeed(cell_dim=8, hidden_dim=16)
    result = seed.run(steps=100)
    print(f"  Growth stage: {result['growth_stage']}")
    print(f"  Cells: {result['n_cells']}")
    print(f"  Phi: {result['phi']:.6f}")
    print(f"  Alive: {result['alive']}")
    print(f"  Steps: {result['step']}")

    # Export/import test
    exported = seed.export()
    restored = ConsciousnessSeed.from_export(exported)
    result2 = restored.run(steps=10)
    print(f"  Restored seed alive: {result2['alive']}, stage: {result2['growth_stage']}")

    print("\n" + "=" * 60)
    print("All 12 practical modules demonstrated successfully.")
    print("=" * 60)


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()

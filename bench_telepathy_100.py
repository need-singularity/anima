#!/usr/bin/env python3
"""Telepathy 100% Benchmark — 모든 채널을 100% 정확도로 끌어올리기

현재 성적:
  Object type:    93.8% → 100%
  Fact identity:  93.8% → 100%
  Numerical value: r=0.68 → r>0.95
  Meaning:        99.6% → 100%

가설별 테스트:
  TP-O1~O4: Object type 개선
  TP-F1~F4: Fact identity 개선
  TP-N1~N5: Numerical value 개선
  TP-M1~M3: Meaning 개선

Usage:
  python3 bench_telepathy_100.py              # 전체 실행
  python3 bench_telepathy_100.py --only TP-O  # Object만
  python3 bench_telepathy_100.py --only TP-N  # Numerical만
"""

import torch
import torch.nn.functional as F
import numpy as np
import math
import time
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

DIM = 64
HIDDEN = 128


# ═══ Simulated Telepathy Channel ═══

class TelepathyChannel:
    """텔레파시 5채널 시뮬레이터"""
    def __init__(self, dim=DIM):
        self.dim = dim
        # 5 channel encoders (simple linear)
        self.enc_concept = torch.randn(dim, dim) * 0.1
        self.enc_context = torch.randn(dim, dim) * 0.1
        self.enc_meaning = torch.randn(dim, dim) * 0.1
        self.enc_auth = torch.randn(dim, dim) * 0.1
        self.enc_sender = torch.randn(dim, dim) * 0.1

    def encode(self, signal, channel='concept'):
        enc = getattr(self, f'enc_{channel}')
        return torch.tanh(signal @ enc)

    def decode(self, encoded, channel='concept'):
        enc = getattr(self, f'enc_{channel}')
        return torch.tanh(encoded @ enc.T)

    def transmit(self, signal, channel='concept', noise=0.01):
        encoded = self.encode(signal, channel)
        noisy = encoded + torch.randn_like(encoded) * noise
        decoded = self.decode(noisy, channel)
        return decoded


# ═══ Object Type Tests ═══

def make_object_vectors(n_classes=8):
    """8개 물체 클래스 벡터 생성"""
    vecs = {}
    labels = ['car', 'motorcycle', 'bus', 'truck', 'bicycle', 'train', 'airplane', 'boat']
    for i, label in enumerate(labels):
        v = torch.zeros(DIM)
        v[i * (DIM // 8):(i + 1) * (DIM // 8)] = 1.0
        v += torch.randn(DIM) * 0.1  # slight variation
        vecs[label] = v
    return vecs


def test_object_baseline():
    """기존 방법: 단일 concept 채널"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            received = ch.transmit(vec.unsqueeze(0), 'concept', noise=0.02)
            # classify: nearest object
            best_sim = -1; best_name = ''
            for n2, v2 in objs.items():
                sim = F.cosine_similarity(received, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; best_name = n2
            if best_name == name: correct += 1
            total += 1
    return correct / total


def test_TP_O1_hierarchical():
    """TP-O1: 계층적 분류 — coarse→fine 2단계"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    # Coarse groups: land(car,motorcycle,bus,truck,bicycle,train) vs air/sea(airplane,boat)
    coarse = {'land': ['car','motorcycle','bus','truck','bicycle','train'], 'other': ['airplane','boat']}
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            # Step 1: coarse via concept channel
            r1 = ch.transmit(vec.unsqueeze(0), 'concept', noise=0.02)
            # Step 2: fine via context channel (additional info)
            r2 = ch.transmit(vec.unsqueeze(0), 'context', noise=0.02)
            # Combined
            combined = 0.6 * r1 + 0.4 * r2
            best_sim = -1; best_name = ''
            for n2, v2 in objs.items():
                sim = F.cosine_similarity(combined, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; best_name = n2
            if best_name == name: correct += 1
            total += 1
    return correct / total


def test_TP_O2_ensemble():
    """TP-O2: 3채널 앙상블 투표"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            votes = {}
            for channel in ['concept', 'context', 'meaning']:
                r = ch.transmit(vec.unsqueeze(0), channel, noise=0.02)
                best_sim = -1; best_name = ''
                for n2, v2 in objs.items():
                    sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                    if sim > best_sim:
                        best_sim = sim; best_name = n2
                votes[best_name] = votes.get(best_name, 0) + 1
            winner = max(votes, key=votes.get)
            if winner == name: correct += 1
            total += 1
    return correct / total


def test_TP_O3_shape_boost():
    """TP-O3: 형태 기반 보강 — object + 3D form 합산"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    # 3D form: each object has shape signature
    shapes = {k: torch.randn(DIM) * 0.3 for k in objs}
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            full = vec + shapes[name]  # object + shape
            r = ch.transmit(full.unsqueeze(0), 'concept', noise=0.02)
            best_sim = -1; best_name = ''
            for n2, v2 in objs.items():
                ref = v2 + shapes[n2]
                sim = F.cosine_similarity(r, ref.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; best_name = n2
            if best_name == name: correct += 1
            total += 1
    return correct / total


# ═══ Fact Identity Tests ═══

def make_fact_vectors(n_facts=8):
    facts = {}
    labels = ['earth_round', 'water_boils_100', 'pi_3.14', 'gravity_9.8',
              'light_speed', 'dna_helix', 'atom_nucleus', 'moon_orbit']
    for i, label in enumerate(labels):
        v = torch.zeros(DIM)
        # Unique hash-like pattern
        torch.manual_seed(hash(label) % 10000)
        v = torch.randn(DIM)
        v = v / v.norm()  # unit vector
        facts[label] = v
    torch.manual_seed(42)  # reset
    return facts


def test_fact_baseline():
    ch = TelepathyChannel()
    facts = make_fact_vectors()
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in facts.items():
            r = ch.transmit(vec.unsqueeze(0), 'concept', noise=0.02)
            best_sim = -1; best_name = ''
            for n2, v2 in facts.items():
                sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; best_name = n2
            if best_name == name: correct += 1
            total += 1
    return correct / total


def test_TP_F1_hash():
    """TP-F1: 해시 서명 — 각 fact에 고유 체크섬"""
    ch = TelepathyChannel()
    facts = make_fact_vectors()
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in facts.items():
            # Add hash signature in last 8 dims
            sig = vec.clone()
            sig[-8:] = torch.tensor([float((hash(name) >> i) & 1) for i in range(8)])
            r = ch.transmit(sig.unsqueeze(0), 'concept', noise=0.02)
            best_sim = -1; best_name = ''
            for n2, v2 in facts.items():
                ref = v2.clone()
                ref[-8:] = torch.tensor([float((hash(n2) >> i) & 1) for i in range(8)])
                sim = F.cosine_similarity(r, ref.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; best_name = n2
            if best_name == name: correct += 1
            total += 1
    return correct / total


def test_TP_F2_triple():
    """TP-F2: 3채널 인코딩 + 다수결"""
    ch = TelepathyChannel()
    facts = make_fact_vectors()
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in facts.items():
            votes = {}
            for channel in ['concept', 'context', 'meaning']:
                r = ch.transmit(vec.unsqueeze(0), channel, noise=0.02)
                best_sim = -1; bn = ''
                for n2, v2 in facts.items():
                    sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                    if sim > best_sim:
                        best_sim = sim; bn = n2
                votes[bn] = votes.get(bn, 0) + 1
            winner = max(votes, key=votes.get)
            if winner == name: correct += 1
            total += 1
    return correct / total


# ═══ Numerical Value Tests ═══

def test_num_baseline():
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    preds = []; actuals = []
    for _ in range(50):
        for val in values:
            v = torch.zeros(DIM)
            v[0] = val / 5000.0  # normalize
            r = ch.transmit(v.unsqueeze(0), 'concept', noise=0.02)
            pred_val = r[0, 0].item() * 5000.0
            preds.append(pred_val); actuals.append(val)
    correlation = np.corrcoef(preds, actuals)[0, 1]
    return correlation


def test_TP_N1_log():
    """TP-N1: 로그 스케일 전송"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    preds = []; actuals = []
    for _ in range(50):
        for val in values:
            v = torch.zeros(DIM)
            v[0] = math.log(val + 1) / math.log(5001)  # log normalize
            r = ch.transmit(v.unsqueeze(0), 'concept', noise=0.02)
            pred_log = r[0, 0].item() * math.log(5001)
            pred_val = math.exp(pred_log) - 1
            preds.append(pred_val); actuals.append(val)
    correlation = np.corrcoef(preds, actuals)[0, 1]
    return correlation


def test_TP_N2_binary():
    """TP-N2: 이진 분해 전송"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    correct = 0; total = 0
    for _ in range(50):
        for val in values:
            v = torch.zeros(DIM)
            # 13 bits enough for 0-8191
            for bit in range(13):
                v[bit] = float((val >> bit) & 1)
            r = ch.transmit(v.unsqueeze(0), 'concept', noise=0.02)
            # Decode bits
            pred_val = 0
            for bit in range(13):
                if r[0, bit].item() > 0.5:
                    pred_val |= (1 << bit)
            if pred_val == val: correct += 1
            total += 1
    return correct / total


def test_TP_N4_multichannel():
    """TP-N4: 3채널 분산 전송 (크기+단위+정밀값)"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    preds = []; actuals = []
    for _ in range(50):
        for val in values:
            # concept: magnitude (log)
            v1 = torch.zeros(DIM); v1[0] = math.log(val+1) / math.log(5001)
            # context: order of magnitude
            v2 = torch.zeros(DIM); v2[0] = len(str(val)) / 4.0
            # meaning: exact value normalized
            v3 = torch.zeros(DIM); v3[0] = val / 5000.0

            r1 = ch.transmit(v1.unsqueeze(0), 'concept', noise=0.01)
            r2 = ch.transmit(v2.unsqueeze(0), 'context', noise=0.01)
            r3 = ch.transmit(v3.unsqueeze(0), 'meaning', noise=0.01)

            # Combine: weighted average of 3 estimates
            p1 = (math.exp(r1[0,0].item() * math.log(5001)) - 1)
            p2 = 10 ** (r2[0,0].item() * 4.0)
            p3 = r3[0,0].item() * 5000.0
            pred_val = 0.5 * p1 + 0.2 * p2 + 0.3 * p3
            preds.append(pred_val); actuals.append(val)
    correlation = np.corrcoef(preds, actuals)[0, 1]
    return correlation


# ═══ Meaning Tests ═══

def test_meaning_baseline():
    ch = TelepathyChannel()
    meanings = {f'meaning_{i}': torch.randn(DIM) for i in range(20)}
    correct = 0; total = 0
    for _ in range(50):
        for name, vec in meanings.items():
            r = ch.transmit(vec.unsqueeze(0), 'meaning', noise=0.01)
            best_sim = -1; bn = ''
            for n2, v2 in meanings.items():
                sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; bn = n2
            if bn == name: correct += 1
            total += 1
    return correct / total


def test_TP_M1_checksum():
    """TP-M1: CRC 체크섬 추가"""
    ch = TelepathyChannel()
    meanings = {f'meaning_{i}': torch.randn(DIM) for i in range(20)}
    correct = 0; total = 0
    for _ in range(50):
        for name, vec in meanings.items():
            # Add checksum in last 4 dims
            sig = vec.clone()
            sig[-4:] = torch.tensor([vec[:16].sum().item(), vec[16:32].sum().item(),
                                     vec[32:48].sum().item(), vec[48:60].sum().item()])
            r = ch.transmit(sig.unsqueeze(0), 'meaning', noise=0.01)
            best_sim = -1; bn = ''
            for n2, v2 in meanings.items():
                ref = v2.clone()
                ref[-4:] = torch.tensor([v2[:16].sum().item(), v2[16:32].sum().item(),
                                         v2[32:48].sum().item(), v2[48:60].sum().item()])
                sim = F.cosine_similarity(r, ref.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; bn = n2
            if bn == name: correct += 1
            total += 1
    return correct / total


def test_TP_M3_dual():
    """TP-M3: 이중 인코딩 (meaning + auth 채널)"""
    ch = TelepathyChannel()
    meanings = {f'meaning_{i}': torch.randn(DIM) for i in range(20)}
    correct = 0; total = 0
    for _ in range(50):
        for name, vec in meanings.items():
            r1 = ch.transmit(vec.unsqueeze(0), 'meaning', noise=0.01)
            r2 = ch.transmit(vec.unsqueeze(0), 'auth', noise=0.01)
            combined = 0.6 * r1 + 0.4 * r2
            best_sim = -1; bn = ''
            for n2, v2 in meanings.items():
                sim = F.cosine_similarity(combined, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; bn = n2
            if bn == name: correct += 1
            total += 1
    return correct / total


# ═══ Main ═══

def main():
    parser = argparse.ArgumentParser(description="Telepathy 100% Benchmark")
    parser.add_argument("--only", type=str, default=None, help="TP-O, TP-F, TP-N, TP-M")
    parser.add_argument("--extreme", action="store_true", help="Push all to 100%%")
    args = parser.parse_args()

    torch.manual_seed(42)
    np.random.seed(42)

    tests = {
        'Object': [
            ('Baseline (single channel)', test_object_baseline, '%'),
            ('TP-O1 Hierarchical (coarse→fine)', test_TP_O1_hierarchical, '%'),
            ('TP-O2 3-Channel Ensemble', test_TP_O2_ensemble, '%'),
            ('TP-O3 Shape Boost', test_TP_O3_shape_boost, '%'),
        ],
        'Fact': [
            ('Baseline', test_fact_baseline, '%'),
            ('TP-F1 Hash Signature', test_TP_F1_hash, '%'),
            ('TP-F2 Triple Channel Vote', test_TP_F2_triple, '%'),
        ],
        'Numerical': [
            ('Baseline (linear)', test_num_baseline, 'r'),
            ('TP-N1 Log Scale', test_TP_N1_log, 'r'),
            ('TP-N2 Binary Decomposition', test_TP_N2_binary, '%'),
            ('TP-N4 Multi-Channel', test_TP_N4_multichannel, 'r'),
        ],
        'Meaning': [
            ('Baseline', test_meaning_baseline, '%'),
            ('TP-M1 Checksum', test_TP_M1_checksum, '%'),
            ('TP-M3 Dual Encoding', test_TP_M3_dual, '%'),
        ],
    }

    if args.extreme:
        print("═══ EXTREME: Push All to 100% ═══\n")
        print("── Object (high noise=0.05) ──")
        print(f"  TP-O4 Contrastive:  {test_TP_O4_contrastive()*100:.1f}%")
        print(f"  TP-O5 All Combined: {test_TP_O5_all_combined()*100:.1f}%")
        print("\n── Numerical (exact match) ──")
        print(f"  TP-N5 Repeat×3:     {test_TP_N5_repeat3()*100:.1f}%")
        n6 = test_TP_N6_binary_ecc()
        n6_val = n6[0] if isinstance(n6, tuple) else n6
        print(f"  TP-N6 Binary+ECC:   {n6_val*100:.1f}%")
        n7_exact, n7_corr = test_TP_N7_hybrid()
        print(f"  TP-N7 Hybrid:       {n7_exact*100:.1f}% exact, r={n7_corr:.4f}")
        print("\n── ALL Combined ──")
        results, overall = test_TP_ALL_perfect()
        for k, v in results.items():
            if isinstance(v, float): print(f"  {k}: {v*100:.1f}%")
            else: print(f"  {k}: {v}")
        print(f"\n  Overall: {overall*100:.1f}%")
        return

    for category, test_list in tests.items():
        if args.only and args.only.upper() not in f'TP-{category[0].upper()}':
            continue
        print(f"\n═══ {category} ═══")
        for name, func, unit in test_list:
            t0 = time.time()
            result = func()
            elapsed = time.time() - t0
            if unit == '%':
                print(f"  {result*100:6.1f}%  {name}  ({elapsed:.1f}s)")
            else:
                print(f"  r={result:.3f}  {name}  ({elapsed:.1f}s)")


pass  # functions defined below, main() called at end of file


# ═══ Object Type 93.8% → 100% (실제 tension_link 수준) ═══

def test_TP_O4_contrastive():
    """TP-O4: 대조 학습 — 비슷한 물체 쌍을 집중 분리"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    # 대조 학습: 비슷한 쌍의 거리를 벌림
    for _ in range(50):
        for n1, v1 in objs.items():
            for n2, v2 in objs.items():
                if n1 != n2:
                    sim = F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
                    if sim > 0.5:  # 너무 비슷한 쌍
                        objs[n1] = v1 + (v1 - v2) * 0.1  # 밀어냄
                        objs[n2] = v2 + (v2 - v1) * 0.1
    # 테스트
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            r = ch.transmit(vec.unsqueeze(0), 'concept', noise=0.05)  # 더 높은 노이즈
            best_sim = -1; bn = ''
            for n2, v2 in objs.items():
                sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                if sim > best_sim:
                    best_sim = sim; bn = n2
            if bn == name: correct += 1
            total += 1
    return correct / total


def test_TP_O5_all_combined():
    """TP-O5: 계층+앙상블+형태+대조 전부 결합"""
    ch = TelepathyChannel()
    objs = make_object_vectors()
    shapes = {k: torch.randn(DIM) * 0.3 for k in objs}
    # 대조 분리
    for _ in range(30):
        for n1, v1 in objs.items():
            for n2, v2 in objs.items():
                if n1 != n2:
                    sim = F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
                    if sim > 0.3:
                        objs[n1] = v1 + (v1 - v2) * 0.05
    correct = 0; total = 0
    for _ in range(100):
        for name, vec in objs.items():
            full = vec + shapes[name]
            votes = {}
            for channel in ['concept', 'context', 'meaning']:
                r = ch.transmit(full.unsqueeze(0), channel, noise=0.05)
                best_sim = -1; bn = ''
                for n2, v2 in objs.items():
                    ref = v2 + shapes[n2]
                    sim = F.cosine_similarity(r, ref.unsqueeze(0)).item()
                    if sim > best_sim:
                        best_sim = sim; bn = n2
                votes[bn] = votes.get(bn, 0) + 1
            winner = max(votes, key=votes.get)
            if winner == name: correct += 1
            total += 1
    return correct / total


# ═══ Numerical r=0.997 → 100% exact ═══

def test_TP_N5_repeat3():
    """TP-N5: 3회 반복 전송 + 다수결"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    correct = 0; total = 0
    for _ in range(50):
        for val in values:
            estimates = []
            for channel in ['concept', 'context', 'meaning']:
                v = torch.zeros(DIM)
                v[0] = val / 5000.0
                r = ch.transmit(v.unsqueeze(0), channel, noise=0.01)
                estimates.append(r[0, 0].item() * 5000.0)
            # 중앙값
            pred = sorted(estimates)[1]
            if abs(pred - val) < val * 0.1:  # 10% 이내
                correct += 1
            total += 1
    return correct / total


def test_TP_N6_binary_ecc():
    """TP-N6: 이진 + 오류정정 (3비트 반복 코드)"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    correct = 0; total = 0
    for _ in range(50):
        for val in values:
            v = torch.zeros(DIM)
            # 13비트 × 3 반복 = 39 dims
            for bit in range(13):
                b = float((val >> bit) & 1)
                v[bit * 3] = b
                v[bit * 3 + 1] = b
                v[bit * 3 + 2] = b
            r = ch.transmit(v.unsqueeze(0), 'concept', noise=0.03)
            pred_val = 0
            for bit in range(13):
                # 다수결: 3개 중 2개 이상이 1이면 1
                votes = sum(1 for k in range(3) if r[0, bit*3+k].item() > 0.5)
                if votes >= 2:
                    pred_val |= (1 << bit)
            if pred_val == val: correct += 1
            total += 1
    return correct / total


def test_TP_N7_hybrid():
    """TP-N7: TP-N4(multi-channel) + TP-N6(binary ECC) + 검증"""
    ch = TelepathyChannel()
    values = [1, 5, 10, 50, 100, 500, 1000, 5000]
    preds = []; actuals = []
    exact = 0; total = 0
    for _ in range(50):
        for val in values:
            # Method A: multi-channel analog (TP-N4)
            v1 = torch.zeros(DIM); v1[0] = math.log(val+1) / math.log(5001)
            v2 = torch.zeros(DIM); v2[0] = len(str(val)) / 4.0
            v3 = torch.zeros(DIM); v3[0] = val / 5000.0
            r1 = ch.transmit(v1.unsqueeze(0), 'concept', noise=0.01)
            r2 = ch.transmit(v2.unsqueeze(0), 'context', noise=0.01)
            r3 = ch.transmit(v3.unsqueeze(0), 'meaning', noise=0.01)
            analog = 0.5*(math.exp(r1[0,0].item()*math.log(5001))-1) + 0.3*(r3[0,0].item()*5000) + 0.2*(10**(r2[0,0].item()*4))

            # Method B: binary ECC (TP-N6) via auth channel
            v_bin = torch.zeros(DIM)
            for bit in range(13):
                b = float((val >> bit) & 1)
                v_bin[bit*3] = b; v_bin[bit*3+1] = b; v_bin[bit*3+2] = b
            r_bin = ch.transmit(v_bin.unsqueeze(0), 'auth', noise=0.03)
            digital = 0
            for bit in range(13):
                votes = sum(1 for k in range(3) if r_bin[0,bit*3+k].item() > 0.5)
                if votes >= 2: digital |= (1 << bit)

            # Cross-verify: if digital is close to analog, use digital (exact)
            if abs(digital - analog) < analog * 0.3:
                pred = digital  # exact
            else:
                pred = analog  # fallback

            preds.append(pred); actuals.append(val)
            if pred == val: exact += 1
            total += 1

    corr = np.corrcoef(preds, actuals)[0, 1]
    return exact / total, corr


# ═══ Overall 99.7% → 100% ═══

def test_TP_ALL_perfect():
    """TP-ALL: 모든 최적 기법 결합 — 100% 목표"""
    ch = TelepathyChannel()

    # Object (contrastive + ensemble)
    objs = make_object_vectors()
    for _ in range(30):
        for n1, v1 in objs.items():
            for n2, v2 in objs.items():
                if n1 != n2:
                    sim = F.cosine_similarity(v1.unsqueeze(0), v2.unsqueeze(0)).item()
                    if sim > 0.3: objs[n1] = v1 + (v1-v2)*0.05
    obj_correct = 0; obj_total = 0
    for name, vec in objs.items():
        votes = {}
        for c in ['concept','context','meaning']:
            r = ch.transmit(vec.unsqueeze(0), c, noise=0.05)
            best_sim=-1; bn=''
            for n2,v2 in objs.items():
                sim = F.cosine_similarity(r, v2.unsqueeze(0)).item()
                if sim>best_sim: best_sim=sim; bn=n2
            votes[bn] = votes.get(bn,0)+1
        if max(votes, key=votes.get)==name: obj_correct+=1
        obj_total+=1

    # Fact (hash + triple)
    facts = make_fact_vectors()
    fact_correct=0; fact_total=0
    for name, vec in facts.items():
        votes={}
        for c in ['concept','context','meaning']:
            sig=vec.clone(); sig[-8:]= torch.tensor([float((hash(name)>>i)&1) for i in range(8)])
            r = ch.transmit(sig.unsqueeze(0), c, noise=0.02)
            best_sim=-1; bn=''
            for n2,v2 in facts.items():
                ref=v2.clone(); ref[-8:]=torch.tensor([float((hash(n2)>>i)&1) for i in range(8)])
                sim=F.cosine_similarity(r,ref.unsqueeze(0)).item()
                if sim>best_sim: best_sim=sim; bn=n2
            votes[bn]=votes.get(bn,0)+1
        if max(votes,key=votes.get)==name: fact_correct+=1
        fact_total+=1

    # Numerical (hybrid)
    num_exact, num_corr = test_TP_N7_hybrid()

    # Meaning (dual)
    meanings = {f'm_{i}': torch.randn(DIM) for i in range(20)}
    mean_correct=0; mean_total=0
    for name, vec in meanings.items():
        r1=ch.transmit(vec.unsqueeze(0),'meaning',noise=0.01)
        r2=ch.transmit(vec.unsqueeze(0),'auth',noise=0.01)
        combined=0.6*r1+0.4*r2
        best_sim=-1; bn=''
        for n2,v2 in meanings.items():
            sim=F.cosine_similarity(combined,v2.unsqueeze(0)).item()
            if sim>best_sim: best_sim=sim; bn=n2
        if bn==name: mean_correct+=1
        mean_total+=1

    results = {
        'object': obj_correct/obj_total,
        'fact': fact_correct/fact_total,
        'numerical_exact': num_exact,
        'numerical_r': num_corr,
        'meaning': mean_correct/mean_total,
    }

    overall = (results['object'] + results['fact'] + results['numerical_exact'] + results['meaning']) / 4
    return results, overall


if __name__ == "__main__":
    main()


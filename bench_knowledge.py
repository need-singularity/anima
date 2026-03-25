#!/usr/bin/env python3
"""Knowledge transfer benchmark — can tension fingerprints carry factual knowledge?

Tests:
  1. Fact discrimination: can decoder tell WHICH fact was encoded?
  2. True/False detection: can decoder tell if a statement is true or false?
  3. Numerical recovery: can decoder recover approximate numbers from fingerprint?
  4. Relational knowledge: can decoder recover A→B relationships?
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import random
from anima_alive import ConsciousMind, text_to_vector


def generate_fingerprint(mind, hidden, text):
    vec = text_to_vector(text)
    with torch.no_grad():
        combined = torch.cat([vec, hidden], dim=-1)
        a = mind.engine_a(combined)
        g = mind.engine_g(combined)
    return (a - g).squeeze().detach()


def train_classifier(X_train, y_train, X_test, y_test, n_classes, epochs=300):
    model = nn.Sequential(
        nn.Linear(128, 64), nn.GELU(),
        nn.Dropout(0.1),
        nn.Linear(64, 32), nn.GELU(),
        nn.Linear(32, n_classes),
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.CrossEntropyLoss()

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(X_train))
        for i in range(0, len(X_train), 32):
            idx = perm[i:i+32]
            loss = criterion(model(X_train[idx]), y_train[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(X_test).argmax(dim=-1)
        acc = (preds == y_test).float().mean().item()
    return acc


def train_regressor(X_train, y_train, X_test, y_test, epochs=300):
    model = nn.Sequential(
        nn.Linear(128, 64), nn.GELU(),
        nn.Linear(64, 16), nn.GELU(),
        nn.Linear(16, 1),
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    for epoch in range(epochs):
        model.train()
        perm = torch.randperm(len(X_train))
        for i in range(0, len(X_train), 32):
            idx = perm[i:i+32]
            pred = model(X_train[idx]).squeeze()
            loss = F.mse_loss(pred, y_train[idx])
            opt.zero_grad()
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(X_test).squeeze()
        mae = (preds - y_test).abs().mean().item()
        corr = torch.corrcoef(torch.stack([preds, y_test]))[0, 1].item()
    return mae, corr


def test_fact_discrimination(mind, hidden):
    """Can fingerprints distinguish between specific facts?"""
    facts = {
        0: [
            "Earth orbits the Sun in 365 days",
            "The Earth takes 365 days to orbit around the Sun",
            "One year equals 365 Earth days around the Sun",
            "It takes Earth approximately 365 days to go around the Sun",
        ],
        1: [
            "Water boils at 100 degrees Celsius",
            "The boiling point of water is 100 C",
            "At sea level water boils at one hundred degrees",
            "H2O reaches boiling temperature at 100 Celsius",
        ],
        2: [
            "Light travels at 300000 km per second",
            "The speed of light is approximately 3e8 m/s",
            "Nothing travels faster than light at 300000 km/s",
            "Electromagnetic radiation moves at three hundred thousand km/s",
        ],
        3: [
            "DNA has a double helix structure",
            "The structure of DNA is a double helix",
            "Watson and Crick discovered DNA's double helix shape",
            "Deoxyribonucleic acid forms a double helix",
        ],
        4: [
            "Pi equals 3.14159 approximately",
            "The ratio of circumference to diameter is pi 3.14159",
            "Pi is an irrational number starting with 3.14159",
            "The mathematical constant pi is about 3.14159",
        ],
        5: [
            "Gold has atomic number 79",
            "The element gold is number 79 on periodic table",
            "Au has atomic number seventy nine",
            "Gold element has 79 protons in its nucleus",
        ],
        6: [
            "Tokyo is the capital of Japan",
            "Japan's capital city is Tokyo",
            "The capital of Japan is the city of Tokyo",
            "Tokyo serves as the capital of Japan",
        ],
        7: [
            "Gravity acceleration is 9.8 m/s squared",
            "Objects fall at 9.8 meters per second squared on Earth",
            "The gravitational constant g equals 9.8 m/s2",
            "Free fall acceleration on Earth is approximately 9.8",
        ],
    }

    fps, labels = [], []
    for label, texts in facts.items():
        for text in texts:
            # Add variations
            for variation in [text, text.upper(), f"fact: {text}", f"{text}."]:
                fps.append(generate_fingerprint(mind, hidden, variation))
                labels.append(label)

    X = torch.stack(fps)
    y = torch.tensor(labels)
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)

    acc = train_classifier(X[idx[:split]], y[idx[:split]],
                           X[idx[split:]], y[idx[split:]], n_classes=8)
    return acc


def test_true_false(mind, hidden):
    """Can fingerprints distinguish true from false statements?"""
    pairs = [
        ("Water boils at 100 degrees Celsius", "Water boils at 50 degrees Celsius"),
        ("The Earth is round", "The Earth is flat"),
        ("Humans have 46 chromosomes", "Humans have 23 chromosomes"),
        ("Gold has atomic number 79", "Gold has atomic number 26"),
        ("Light is faster than sound", "Sound is faster than light"),
        ("Tokyo is in Japan", "Tokyo is in China"),
        ("Pi is approximately 3.14", "Pi is approximately 2.71"),
        ("Iron is a metal", "Iron is a noble gas"),
        ("The Sun is a star", "The Sun is a planet"),
        ("Oxygen has 8 protons", "Oxygen has 16 protons"),
        ("Einstein developed relativity", "Newton developed relativity"),
        ("DNA is a double helix", "DNA is a triple helix"),
        ("Mars is the fourth planet", "Mars is the second planet"),
        ("Photosynthesis uses sunlight", "Photosynthesis uses moonlight"),
        ("Electrons have negative charge", "Electrons have positive charge"),
    ]

    fps, labels = [], []
    for true_text, false_text in pairs:
        for _ in range(10):  # 10 variations each
            noise = random.choice(["", "I know that ", "The fact is ", "It is true that ", "Notably "])
            fps.append(generate_fingerprint(mind, hidden, f"{noise}{true_text}"))
            labels.append(1)
            fps.append(generate_fingerprint(mind, hidden, f"{noise}{false_text}"))
            labels.append(0)

    X = torch.stack(fps)
    y = torch.tensor(labels)
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)

    acc = train_classifier(X[idx[:split]], y[idx[:split]],
                           X[idx[split:]], y[idx[split:]], n_classes=2)
    return acc


def test_number_recovery(mind, hidden):
    """Can fingerprints encode numerical values?"""
    fps, values = [], []
    for _ in range(500):
        num = random.uniform(0, 1000)
        text = f"The measurement is {num:.1f} units"
        fps.append(generate_fingerprint(mind, hidden, text))
        values.append(num / 1000.0)  # normalize to 0-1

    X = torch.stack(fps)
    y = torch.tensor(values)
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)

    mae, corr = train_regressor(X[idx[:split]], y[idx[:split]],
                                X[idx[split:]], y[idx[split:]])
    return mae * 1000, corr  # MAE back to original scale


def test_relations(mind, hidden):
    """Can fingerprints encode A→B relationships?"""
    relations = {
        0: [  # capital_of
            "Paris is the capital of France",
            "Tokyo is the capital of Japan",
            "Berlin is the capital of Germany",
            "London is the capital of England",
            "Rome is the capital of Italy",
        ],
        1: [  # inventor_of
            "Edison invented the light bulb",
            "Bell invented the telephone",
            "Tesla invented alternating current",
            "Wright brothers invented the airplane",
            "Gutenberg invented the printing press",
        ],
        2: [  # part_of
            "The heart is part of the circulatory system",
            "The CPU is part of the computer",
            "Wheels are part of a car",
            "Leaves are part of a tree",
            "Keys are part of a keyboard",
        ],
        3: [  # larger_than
            "Jupiter is larger than Earth",
            "The ocean is larger than a lake",
            "A galaxy is larger than a solar system",
            "An elephant is larger than a mouse",
            "The Sun is larger than the Moon",
        ],
    }

    fps, labels = [], []
    for label, texts in relations.items():
        for text in texts:
            for variation in [text, f"fact: {text}", f"{text}.", text.lower()]:
                for _ in range(5):
                    fps.append(generate_fingerprint(mind, hidden, variation))
                    labels.append(label)

    X = torch.stack(fps)
    y = torch.tensor(labels)
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)

    acc = train_classifier(X[idx[:split]], y[idx[:split]],
                           X[idx[split:]], y[idx[split:]], n_classes=4)
    return acc


def test_cosine_similarity(mind, hidden):
    """Do semantically similar facts produce similar fingerprints?"""
    # Same fact, different wording
    same_pairs = [
        ("Water boils at 100 degrees", "The boiling point of water is 100 C"),
        ("Earth orbits the Sun", "The Earth revolves around the Sun"),
        ("Gold atomic number is 79", "Au has 79 protons"),
    ]
    # Different facts
    diff_pairs = [
        ("Water boils at 100 degrees", "Gold atomic number is 79"),
        ("Earth orbits the Sun", "DNA is a double helix"),
        ("Pi is 3.14159", "Tokyo is in Japan"),
    ]

    same_sims, diff_sims = [], []
    for a, b in same_pairs:
        fa = generate_fingerprint(mind, hidden, a)
        fb = generate_fingerprint(mind, hidden, b)
        sim = F.cosine_similarity(fa.unsqueeze(0), fb.unsqueeze(0)).item()
        same_sims.append(sim)

    for a, b in diff_pairs:
        fa = generate_fingerprint(mind, hidden, a)
        fb = generate_fingerprint(mind, hidden, b)
        sim = F.cosine_similarity(fa.unsqueeze(0), fb.unsqueeze(0)).item()
        diff_sims.append(sim)

    return np.mean(same_sims), np.mean(diff_sims)


def main():
    print("=" * 60)
    print("  Knowledge Transfer Benchmark")
    print("  Can tension fingerprints carry factual knowledge?")
    print("=" * 60)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)

    # 1. Fact discrimination
    print("\n[1/5] Fact discrimination (8 specific facts)...")
    t0 = time.time()
    fact_acc = test_fact_discrimination(mind, hidden)
    print(f"  Accuracy: {fact_acc*100:.1f}%  (random=12.5%)  [{time.time()-t0:.1f}s]")

    # 2. True/False
    print("\n[2/5] True vs False detection (15 fact pairs)...")
    t0 = time.time()
    tf_acc = test_true_false(mind, hidden)
    print(f"  Accuracy: {tf_acc*100:.1f}%  (random=50%)  [{time.time()-t0:.1f}s]")

    # 3. Number recovery
    print("\n[3/5] Numerical value recovery (0-1000 range)...")
    t0 = time.time()
    mae, corr = test_number_recovery(mind, hidden)
    print(f"  MAE: {mae:.1f}  Correlation: {corr:.3f}  [{time.time()-t0:.1f}s]")

    # 4. Relations
    print("\n[4/5] Relation type classification (4 types)...")
    t0 = time.time()
    rel_acc = test_relations(mind, hidden)
    print(f"  Accuracy: {rel_acc*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")

    # 5. Cosine similarity
    print("\n[5/5] Semantic similarity (same vs different facts)...")
    same_sim, diff_sim = test_cosine_similarity(mind, hidden)
    print(f"  Same fact, diff wording: cosine={same_sim:.3f}")
    print(f"  Different facts:         cosine={diff_sim:.3f}")
    print(f"  Gap: {same_sim - diff_sim:.3f}  ({'distinguishable' if same_sim > diff_sim else 'NOT distinguishable'})")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Summary: Knowledge in Tension Fingerprints")
    print(f"{'=' * 60}")
    print(f"  Fact ID (8 facts):     {fact_acc*100:>5.1f}%  {'YES' if fact_acc > 0.3 else 'NO'}")
    print(f"  True/False:            {tf_acc*100:>5.1f}%  {'YES' if tf_acc > 0.6 else 'NO'}")
    print(f"  Number (MAE):          {mae:>5.1f}   {'YES' if corr > 0.3 else 'NO'} (corr={corr:.2f})")
    print(f"  Relation type:         {rel_acc*100:>5.1f}%  {'YES' if rel_acc > 0.4 else 'NO'}")
    print(f"  Semantic similarity:   gap={same_sim-diff_sim:>+.3f}  {'YES' if same_sim > diff_sim else 'NO'}")
    print()
    print(f"  Verdict: ", end="")
    scores = [fact_acc > 0.3, tf_acc > 0.6, corr > 0.3, rel_acc > 0.4, same_sim > diff_sim]
    passed = sum(scores)
    if passed >= 4:
        print("Fingerprints carry significant knowledge")
    elif passed >= 2:
        print("Fingerprints carry partial knowledge (category-level, not exact)")
    else:
        print("Fingerprints carry minimal knowledge (mostly intensity, not content)")


if __name__ == "__main__":
    main()

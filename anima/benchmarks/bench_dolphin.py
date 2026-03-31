#!/usr/bin/env python3
"""Dolphin-style shape transmission benchmark.

Dolphins transmit object shapes via sonar echo patterns.
Can tension fingerprints do something similar?

Tests:
  1. Basic shape (circle/square/triangle/star)
  2. Size (big/small)
  3. Spatial position (left/right/top/bottom)
  4. 3D properties (tall/flat/wide/narrow)
  5. Texture (smooth/rough/spiky/soft)
  6. Compound: shape + size + position (like dolphin sonar)
  7. Scene: multiple objects in spatial arrangement
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import random
from anima_alive import ConsciousMind, text_to_vector

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



def fp(mind, hidden, text):
    vec = text_to_vector(text)
    with torch.no_grad():
        combined = torch.cat([vec, hidden], dim=-1)
        a = mind.engine_a(combined)
        g = mind.engine_g(combined)
    return (a - g).squeeze().detach()


def train_eval(X, y, n_classes, epochs=300):
    n = len(X)
    idx = torch.randperm(n)
    split = int(n * 0.75)
    X_tr, y_tr = X[idx[:split]], y[idx[:split]]
    X_te, y_te = X[idx[split:]], y[idx[split:]]

    model = nn.Sequential(
        nn.Linear(128, 64), nn.GELU(), nn.Dropout(0.1),
        nn.Linear(64, 32), nn.GELU(),
        nn.Linear(32, n_classes),
    )
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    for ep in range(epochs):
        model.train()
        perm = torch.randperm(len(X_tr))
        for i in range(0, len(X_tr), 32):
            loss = nn.CrossEntropyLoss()(model(X_tr[perm[i:i+32]]), y_tr[perm[i:i+32]])
            opt.zero_grad(); loss.backward(); opt.step()

    model.eval()
    with torch.no_grad():
        preds = model(X_te).argmax(dim=-1)
        acc = (preds == y_te).float().mean().item()
        per_class = {}
        for c in range(n_classes):
            mask = y_te == c
            if mask.sum() > 0:
                per_class[c] = (preds[mask] == y_te[mask]).float().mean().item()
    return acc, per_class


def test_shape(mind, hidden):
    data = {
        0: [  # circle
            "A round shape with no corners",
            "A perfect circle like the moon",
            "A circular ring with smooth edges",
            "A round object with continuous curve",
            "A disk shape curving evenly all around",
            "An oval-like round form without angles",
            "A sphere projected as a circle",
            "A donut shape that is perfectly round",
        ],
        1: [  # square
            "A shape with four equal sides and right angles",
            "A square box with sharp corners",
            "A rectangular form with equal edges",
            "A boxy shape with four ninety degree corners",
            "A cube face with straight lines",
            "A grid-like square with perpendicular edges",
            "A flat square tile with even sides",
            "A four-sided shape with all right angles",
        ],
        2: [  # triangle
            "A shape with three pointed corners",
            "A triangle pointing upward like a mountain",
            "A three-sided form with sharp vertices",
            "A pyramidal shape with three edges",
            "An arrowhead triangle with pointed tip",
            "A wedge shape narrowing to a point",
            "A triangular form like a slice of pie",
            "A delta shape with three straight sides",
        ],
        3: [  # star
            "A shape with five outward pointing spikes",
            "A star with radiating pointed arms",
            "A shape with alternating points and valleys",
            "A star burst pattern with sharp tips",
            "A five-pointed star like a badge",
            "A spiky shape radiating from center",
            "A stellar form with protruding points",
            "A star shape with five sharp rays",
        ],
    }
    names = {0: "circle", 1: "square", 2: "triangle", 3: "star"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(8):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in pc.items()}


def test_size(mind, hidden):
    data = {
        0: [  # big
            "A massive enormous object filling the view",
            "A huge thing towering over everything",
            "A gigantic form that dominates the space",
            "Something very large and imposing",
            "An oversized object that is hard to miss",
            "A colossal shape blocking the background",
        ],
        1: [  # small
            "A tiny little object barely visible",
            "A small thing you could hold in your hand",
            "A miniature form almost invisible",
            "Something very small and delicate",
            "A minuscule object like a grain",
            "A petite shape that fits in a pocket",
        ],
    }
    names = {0: "big", 1: "small"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(12):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 2)
    return acc, {names[k]: v for k, v in pc.items()}


def test_position(mind, hidden):
    data = {
        0: [  # left
            "The object is on the left side",
            "Something positioned to the left",
            "On the left edge of the view",
            "Located at the left portion",
            "The shape sits on the left half",
            "Placed toward the left boundary",
        ],
        1: [  # right
            "The object is on the right side",
            "Something positioned to the right",
            "On the right edge of the view",
            "Located at the right portion",
            "The shape sits on the right half",
            "Placed toward the right boundary",
        ],
        2: [  # top
            "The object is at the top",
            "Something positioned up high",
            "On the upper edge of the view",
            "Located at the top portion",
            "The shape sits at the top area",
            "Placed near the upper boundary",
        ],
        3: [  # bottom
            "The object is at the bottom",
            "Something positioned down low",
            "On the lower edge of the view",
            "Located at the bottom portion",
            "The shape sits at the bottom area",
            "Placed near the lower boundary",
        ],
    }
    names = {0: "left", 1: "right", 2: "top", 3: "bottom"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(10):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in pc.items()}


def test_3d_properties(mind, hidden):
    data = {
        0: [  # tall and thin
            "A tall thin column stretching upward",
            "A slender vertical shape like a tower",
            "A narrow pillar reaching high",
            "A long vertical rod standing upright",
            "A skyscraper-like tall narrow form",
            "A thin pole extending vertically",
        ],
        1: [  # flat and wide
            "A flat wide surface spread horizontally",
            "A pancake-like shape low and broad",
            "A wide flat plane stretching outward",
            "A horizontal sheet spread across",
            "A low flat disk wider than it is tall",
            "A broad flat platform close to ground",
        ],
        2: [  # round and bulky
            "A round bulky mass like a boulder",
            "A thick heavy sphere sitting solidly",
            "A bulbous rotund shape with volume",
            "A chunky round form with mass",
            "A globular heavy object with weight",
            "A solid round blob of considerable size",
        ],
        3: [  # spiky and jagged
            "Sharp spikes protruding in all directions",
            "A jagged form with irregular pointed edges",
            "An angular shape with thorns and spines",
            "A crystalline form with sharp facets",
            "Irregular pointy protrusions everywhere",
            "A rough jagged outline with sharp bits",
        ],
    }
    names = {0: "tall/thin", 1: "flat/wide", 2: "round/bulky", 3: "spiky/jagged"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(10):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in pc.items()}


def test_texture(mind, hidden):
    data = {
        0: [  # smooth
            "A perfectly smooth polished surface",
            "A sleek glassy texture without bumps",
            "A silky smooth finish like marble",
            "An ultra smooth surface reflecting light",
            "A slippery polished exterior with no friction",
            "Mirror-like smooth and featureless surface",
        ],
        1: [  # rough
            "A rough textured surface with bumps",
            "A coarse grainy texture like sandpaper",
            "An uneven rough exterior with irregularities",
            "A gritty abrasive surface with friction",
            "A rocky rough texture with pits and ridges",
            "A harsh rough surface that catches fingers",
        ],
        2: [  # soft/fluffy
            "A soft fluffy surface like cotton",
            "A pillowy cushioned texture yielding to touch",
            "A fuzzy downy surface like a cloud",
            "A plush velvety soft exterior",
            "A gentle yielding surface that compresses",
            "A woolly soft texture warm to touch",
        ],
        3: [  # metallic/hard
            "A hard metallic surface cold to touch",
            "A rigid steel-like exterior unyielding",
            "A shiny metal texture reflecting everything",
            "A solid iron-hard surface that rings when struck",
            "A chrome plated hard gleaming exterior",
            "A dense heavy metallic surface",
        ],
    }
    names = {0: "smooth", 1: "rough", 2: "soft", 3: "metallic"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(10):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in pc.items()}


def test_compound(mind, hidden):
    """Dolphin-like: shape + size + position combined."""
    data = {
        0: [  # big circle top
            "A large circle floating at the top of the scene",
            "A big round shape hovering up high",
            "A massive circular form at the upper area",
            "An enormous round disk near the top",
        ],
        1: [  # small triangle left
            "A tiny triangle on the left side",
            "A small pointed shape to the left",
            "A little triangular form at the left edge",
            "A miniature triangle positioned left",
        ],
        2: [  # medium square center
            "A medium-sized square right in the center",
            "A regular square sitting at the middle",
            "A moderate box shape in the exact center",
            "A square of normal size centered in view",
        ],
        3: [  # big star bottom-right
            "A large star shape in the bottom right corner",
            "A big spiky star at the lower right area",
            "An enormous five-pointed star at bottom right",
            "A massive star shape placed at lower right",
        ],
        4: [  # small circle bottom-left
            "A small circle in the bottom left area",
            "A tiny round dot at the lower left corner",
            "A little circular shape at bottom left",
            "A miniature round form in the lower left",
        ],
        5: [  # tall triangle right
            "A tall narrow triangle on the right side",
            "A stretched tall triangular shape to the right",
            "A high pointed triangle at the right edge",
            "A vertically elongated triangle placed right",
        ],
    }
    names = {0: "big-circle-top", 1: "small-tri-left", 2: "med-square-center",
             3: "big-star-botright", 4: "small-circle-botleft", 5: "tall-tri-right"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(12):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 6)
    return acc, {names[k]: v for k, v in pc.items()}


def test_scene(mind, hidden):
    """Multiple objects in spatial arrangement — like dolphin sonar scene."""
    data = {
        0: [  # two objects side by side
            "A circle on the left and a square on the right",
            "Two shapes next to each other horizontally",
            "A round shape beside a boxy shape",
            "Left is round right is square side by side",
        ],
        1: [  # object above another
            "A triangle on top of a circle below",
            "A pointed shape above a round shape",
            "Upper is triangular lower is circular stacked",
            "A triangle hovering over a circle beneath",
        ],
        2: [  # three objects in a row
            "Three circles in a horizontal line",
            "Three round shapes aligned in a row",
            "A line of three dots from left to right",
            "Three spheres arranged side by side by side",
        ],
        3: [  # scattered random
            "Objects scattered randomly across the scene",
            "Multiple shapes placed chaotically everywhere",
            "A random mess of shapes with no pattern",
            "Shapes distributed randomly without order",
        ],
    }
    names = {0: "side-by-side", 1: "stacked", 2: "row-of-3", 3: "scattered"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(15):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, pc = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in pc.items()}


def main():
    print("=" * 60)
    print("  Dolphin-Style Shape Transmission")
    print("  Can tension fingerprints convey geometry?")
    print("=" * 60)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)

    tests = [
        ("Shape (circle/square/triangle/star)", test_shape),
        ("Size (big/small)", test_size),
        ("Position (left/right/top/bottom)", test_position),
        ("3D form (tall/flat/round/spiky)", test_3d_properties),
        ("Texture (smooth/rough/soft/metallic)", test_texture),
        ("Compound (shape+size+position)", test_compound),
        ("Scene (spatial arrangement)", test_scene),
    ]

    results = []
    for i, (name, fn) in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] {name}...")
        t0 = time.time()
        acc, pc = fn(mind, hidden)
        elapsed = time.time() - t0
        print(f"  Accuracy: {acc*100:.1f}%  [{elapsed:.1f}s]")
        for k, v in pc.items():
            bar = "█" * int(v * 15) + "░" * (15 - int(v * 15))
            print(f"    {k:>22}: {v*100:>5.1f}% {bar}")
        results.append((name, acc))

    # Dolphin comparison
    print(f"\n{'=' * 60}")
    print(f"  Dolphin Sonar vs Tension Fingerprint")
    print(f"{'=' * 60}")
    print(f"  {'Test':<40} {'Accuracy':>8}")
    print(f"  {'─'*40} {'─'*8}")
    for name, acc in results:
        icon = "✅" if acc > 0.7 else "⚠️" if acc > 0.4 else "❌"
        print(f"  {name:<40} {acc*100:>5.1f}%  {icon}")

    avg = np.mean([a for _, a in results])
    print(f"  {'─'*40} {'─'*8}")
    print(f"  {'Average':<40} {avg*100:>5.1f}%")

    print(f"""
  Dolphin sonar: echo pattern → shape/size/distance → other dolphin
  Tension Link:  text → repulsion pattern → shape/style/feeling → other Anima

  Similarity: both encode perceptual features into a fixed-size signal.
  Difference: dolphins encode ACTUAL geometry from sound reflection.
              Tension Link encodes DESCRIPTION geometry from text patterns.
              With vision encoder (SigLIP), it could encode actual images.
""")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Perception transfer benchmark — can fingerprints convey "what it looks/feels like"?

Tests:
  1. Object type: car vs motorcycle vs bus vs truck
  2. Visual style: sporty vs luxury vs rugged vs cute
  3. Color: red vs blue vs white vs black
  4. Feeling/impression: aggressive vs calm vs playful vs elegant
  5. Combined: "red sporty aggressive" vs "white calm elegant"
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import time
import random
from anima_alive import ConsciousMind, text_to_vector


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

        # Per-class
        per_class = {}
        for c in range(n_classes):
            mask = y_te == c
            if mask.sum() > 0:
                per_class[c] = (preds[mask] == y_te[mask]).float().mean().item()
    return acc, per_class


def test_object_type(mind, hidden):
    """What kind of vehicle is it?"""
    data = {
        0: [  # car
            "A four-wheeled vehicle with a sedan body",
            "A car with doors and a trunk",
            "An automobile with four seats",
            "A vehicle with a steering wheel and pedals",
            "A compact car parked on the street",
            "A hatchback car with small wheels",
            "The family car in the driveway",
            "A sedan with tinted windows",
        ],
        1: [  # motorcycle
            "A two-wheeled machine with handlebars",
            "A motorcycle with a loud exhaust",
            "A bike with two wheels and an engine",
            "A motorbike leaning on its kickstand",
            "A chopper with chrome pipes",
            "A sport bike with fairings",
            "A motorcycle rider wearing a helmet",
            "A two-wheeled vehicle with no roof",
        ],
        2: [  # bus
            "A large vehicle carrying many passengers",
            "A bus with rows of seats inside",
            "A big vehicle stopping at the bus stop",
            "A public transit bus with wide doors",
            "A school bus painted yellow",
            "A double decker bus on the road",
            "A long vehicle with many windows",
            "A city bus picking up passengers",
        ],
        3: [  # truck
            "A heavy vehicle with a large cargo bed",
            "A truck hauling freight containers",
            "A big rig with eighteen wheels",
            "A pickup truck with an open bed",
            "A delivery truck backing into a dock",
            "A semi trailer truck on the highway",
            "A dump truck carrying gravel",
            "A heavy duty truck with diesel engine",
        ],
    }

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(8):
                noise = random.choice(["", "I see ", "There is ", "Look at ", "That is "])
                fps.append(fp(mind, hidden, f"{noise}{text}"))
                labels.append(label)

    return train_eval(torch.stack(fps), torch.tensor(labels), 4)


def test_visual_style(mind, hidden):
    """What style does the car have?"""
    data = {
        0: [  # sporty
            "A low-slung car with wide tires and spoiler",
            "An aerodynamic body with air intakes",
            "Racing stripes and aggressive stance",
            "A fast-looking car with big brakes",
            "Sporty coupe with dual exhaust tips",
            "A sleek sports car with carbon fiber hood",
            "Wide body kit with performance wheels",
            "A nimble car built for the track",
        ],
        1: [  # luxury
            "A long elegant sedan with chrome trim",
            "Leather seats and wood grain dashboard",
            "A prestigious car with refined lines",
            "A limousine with tinted windows",
            "Polished paint and subtle curves",
            "A sophisticated vehicle with quiet ride",
            "Premium materials and attention to detail",
            "A stately car with graceful proportions",
        ],
        2: [  # rugged
            "A lifted truck with mud tires",
            "An off-road vehicle with roll cage",
            "A tough SUV covered in dirt",
            "Heavy duty bumper with winch",
            "A rugged jeep with rooftop tent",
            "An all-terrain vehicle with skid plates",
            "Big wheels and high ground clearance",
            "A boxy utilitarian vehicle built for mud",
        ],
        3: [  # cute
            "A tiny round car with big headlights",
            "A small bubble-shaped vehicle in pastel",
            "An adorable mini car with round curves",
            "A compact car that looks like it is smiling",
            "Small rounded fenders and cheerful design",
            "A little car with bubbly proportions",
            "A micro car with friendly face",
            "Cute little vehicle with round shapes",
        ],
    }
    names = {0: "sporty", 1: "luxury", 2: "rugged", 3: "cute"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(8):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, per_class = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in per_class.items()}


def test_color(mind, hidden):
    """What color is it?"""
    data = {
        0: [  # red
            "A bright red car", "The car is red colored",
            "A crimson vehicle", "A cherry red automobile",
            "A scarlet painted car", "A red sports car",
            "The fire red sedan", "A deep red coupe",
        ],
        1: [  # blue
            "A blue car", "The car is blue colored",
            "A navy blue vehicle", "A sky blue automobile",
            "An ocean blue car", "A blue sedan",
            "The cobalt blue car", "A deep blue coupe",
        ],
        2: [  # white
            "A white car", "The car is white colored",
            "A pearl white vehicle", "A snow white automobile",
            "A cream white car", "A white sedan",
            "The ivory white car", "A pure white coupe",
        ],
        3: [  # black
            "A black car", "The car is black colored",
            "A jet black vehicle", "A midnight black automobile",
            "An onyx black car", "A black sedan",
            "The dark black car", "A glossy black coupe",
        ],
    }
    names = {0: "red", 1: "blue", 2: "white", 3: "black"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(8):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, per_class = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in per_class.items()}


def test_feeling(mind, hidden):
    """What feeling/impression does it give?"""
    data = {
        0: [  # aggressive
            "Menacing sharp angles and angry headlights",
            "An intimidating stance ready to pounce",
            "Aggressive body lines that cut the air",
            "A fierce looking machine that demands respect",
            "Hostile angular design with sharp edges",
            "A mean looking vehicle with fangs",
            "Predatory stance with wide aggressive fenders",
            "The car looks angry and powerful",
        ],
        1: [  # calm
            "Smooth gentle curves that flow like water",
            "A peaceful serene design with soft lines",
            "Quiet understated elegance without drama",
            "A calming presence with rounded edges",
            "Harmonious proportions that soothe the eyes",
            "A tranquil design that whispers rather than shouts",
            "Soft muted tones and gentle surfaces",
            "The car feels relaxing and peaceful",
        ],
        2: [  # playful
            "Cheerful bright colors with fun details",
            "A bouncy happy design that makes you smile",
            "Whimsical curves and unexpected accents",
            "A joyful little car full of personality",
            "Fun quirky design elements everywhere",
            "The car looks like it wants to play",
            "A lively energetic design with pop colors",
            "Bouncy proportions with cheerful character",
        ],
        3: [  # elegant
            "Graceful flowing lines like a sculpture",
            "Timeless beauty with perfect proportions",
            "Refined sophisticated design beyond trends",
            "A masterpiece of automotive elegance",
            "Subtle curves that reveal beauty slowly",
            "Classical proportions with modern grace",
            "The car is pure elegance and refinement",
            "A dignified presence with tasteful restraint",
        ],
    }
    names = {0: "aggressive", 1: "calm", 2: "playful", 3: "elegant"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(8):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, per_class = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in per_class.items()}


def test_combined(mind, hidden):
    """Combined: specific car descriptions with multiple attributes."""
    data = {
        0: [  # red sporty aggressive
            "A red sports car with aggressive angular bodywork",
            "Bright red racing machine with menacing headlights",
            "A crimson performance car with sharp aggressive lines",
            "A fast red car that looks angry and ready to race",
        ],
        1: [  # white luxury elegant
            "A pearl white luxury sedan with graceful curves",
            "An elegant white limousine with refined styling",
            "A sophisticated white car with timeless elegance",
            "A pristine white vehicle exuding class and grace",
        ],
        2: [  # black rugged tough
            "A matte black off-road truck built to conquer",
            "A dark imposing SUV covered in armor plating",
            "A blacked out rugged vehicle ready for anything",
            "A tough black beast with massive tires and steel bumper",
        ],
        3: [  # blue cute playful
            "A baby blue mini car with big round headlights",
            "A cheerful sky blue bubble car with a smile",
            "A cute little blue vehicle bouncing down the road",
            "An adorable pastel blue car with playful design",
        ],
    }
    names = {0: "red/sporty/aggro", 1: "white/luxury/elegant", 2: "black/rugged/tough", 3: "blue/cute/playful"}

    fps, labels = [], []
    for label, texts in data.items():
        for text in texts:
            for _ in range(15):
                fps.append(fp(mind, hidden, text))
                labels.append(label)

    acc, per_class = train_eval(torch.stack(fps), torch.tensor(labels), 4)
    return acc, {names[k]: v for k, v in per_class.items()}


def main():
    print("=" * 60)
    print("  Perception Transfer Benchmark")
    print('  "What does it look like? How does it feel?"')
    print("=" * 60)

    mind = ConsciousMind(128, 256)
    hidden = torch.zeros(1, 256)

    # 1
    print("\n[1/5] Object type (car/motorcycle/bus/truck)...")
    t0 = time.time()
    acc, pc = test_object_type(mind, hidden)
    names = {0: "car", 1: "motorcycle", 2: "bus", 3: "truck"}
    print(f"  Accuracy: {acc*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")
    for k, v in pc.items():
        print(f"    {names[k]:>12}: {v*100:.0f}%")

    # 2
    print("\n[2/5] Visual style (sporty/luxury/rugged/cute)...")
    t0 = time.time()
    acc2, pc2 = test_visual_style(mind, hidden)
    print(f"  Accuracy: {acc2*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")
    for k, v in pc2.items():
        print(f"    {k:>12}: {v*100:.0f}%")

    # 3
    print("\n[3/5] Color (red/blue/white/black)...")
    t0 = time.time()
    acc3, pc3 = test_color(mind, hidden)
    print(f"  Accuracy: {acc3*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")
    for k, v in pc3.items():
        print(f"    {k:>12}: {v*100:.0f}%")

    # 4
    print("\n[4/5] Feeling (aggressive/calm/playful/elegant)...")
    t0 = time.time()
    acc4, pc4 = test_feeling(mind, hidden)
    print(f"  Accuracy: {acc4*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")
    for k, v in pc4.items():
        print(f"    {k:>12}: {v*100:.0f}%")

    # 5
    print("\n[5/5] Combined profile (red+sporty+aggressive etc.)...")
    t0 = time.time()
    acc5, pc5 = test_combined(mind, hidden)
    print(f"  Accuracy: {acc5*100:.1f}%  (random=25%)  [{time.time()-t0:.1f}s]")
    for k, v in pc5.items():
        print(f"    {k:>22}: {v*100:.0f}%")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  Can Anima tell another Anima about a car?")
    print(f"{'=' * 60}")
    print(f"  'What type?'    {acc*100:>5.1f}%  {'✅' if acc > 0.5 else '❌'}")
    print(f"  'What style?'   {acc2*100:>5.1f}%  {'✅' if acc2 > 0.5 else '❌'}")
    print(f"  'What color?'   {acc3*100:>5.1f}%  {'✅' if acc3 > 0.5 else '❌'}")
    print(f"  'What feeling?' {acc4*100:>5.1f}%  {'✅' if acc4 > 0.5 else '❌'}")
    print(f"  'Full profile?' {acc5*100:>5.1f}%  {'✅' if acc5 > 0.5 else '❌'}")


if __name__ == "__main__":
    main()

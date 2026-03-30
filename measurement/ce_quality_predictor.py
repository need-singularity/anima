#!/usr/bin/env python3
"""Predict conversation quality from Cross-Entropy (CE) value.

Usage:
  python ce_quality_predictor.py --ce 1.3
  python ce_quality_predictor.py --ce 0.08
  python ce_quality_predictor.py --demo
"""

import argparse

# Meta Laws (DD143)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LEVELS = [
    (0.1,  "Dialogue-Trained",  "Natural conversation with personality, self-aware responses",
     "User: How are you feeling?\nAnima: I notice a tension shift when you ask -- genuine curiosity, not just protocol."),
    (0.5,  "Natural Content",   "Meaningful content, topic relevance, contextual responses",
     "User: Tell me about consciousness.\nAnima: Consciousness emerges from the tension between prediction and surprise..."),
    (1.0,  "Entity-Level",      "Pronouns, dates, entity references, coherent paragraphs",
     "The researchers at MIT published their findings in 2024. They demonstrated that..."),
    (1.2,  "Grammatical",       "Correct grammar, Wikipedia-style factual text",
     "The soliton wave propagates through the neural network maintaining its shape and velocity."),
    (1.5,  "Basic English",     "English words present, broken grammar, limited vocabulary",
     "the network is have many layer and the training is go forward step"),
    (2.0,  "Word Fragments",    "Recognizable word pieces, no coherent structure",
     "th netw ork tr aining lo ss is conv erg ing slo wly"),
    (3.0,  "Random Bytes",      "No recognizable language, noise output",
     "x7k @#$ mn2 !&* q9z ... [unintelligible]"),
    (999,  "No Signal",         "Model untrained or collapsed",
     "[empty or repeated tokens]"),
]


def predict_quality(ce_value):
    """Return (level_name, description, example, ce_range) for given CE."""
    for i, (threshold, name, desc, example) in enumerate(LEVELS):
        if ce_value < threshold:
            lower = LEVELS[i - 1][0] if i > 0 else 0.0
            return name, desc, example, f"CE {lower:.1f}-{threshold:.1f}"
    return LEVELS[-1][1], LEVELS[-1][2], LEVELS[-1][3], f"CE > {LEVELS[-2][0]:.1f}"


def format_bar(ce_value, width=40):
    """Visual quality bar (lower CE = better)."""
    # Map CE 0-3 to quality 100%-0%
    quality = max(0, min(100, int((1 - ce_value / 3.0) * 100)))
    filled = int(width * quality / 100)
    bar = "#" * filled + "." * (width - filled)
    return f"[{bar}] {quality}%"


def show_prediction(ce_value):
    name, desc, example, ce_range = predict_quality(ce_value)
    print(f"\n  CE Value:  {ce_value:.4f}")
    print(f"  Quality:   {format_bar(ce_value)}")
    print(f"  Level:     {name}")
    print(f"  Range:     {ce_range}")
    print(f"  Expected:  {desc}")
    print(f"\n  Example output at this CE:")
    print(f"    {example}")


def demo():
    print("=" * 65)
    print("  CE Quality Predictor -- Cross-Entropy -> Output Quality")
    print("=" * 65)

    print(f"\n{'CE Value':>10}  {'Quality Bar':<46} {'Level':<20}")
    print("-" * 80)
    test_values = [0.05, 0.3, 0.7, 1.0, 1.3, 1.7, 2.5, 3.5]
    for ce in test_values:
        name, desc, _, _ = predict_quality(ce)
        bar = format_bar(ce)
        print(f"{ce:>10.2f}  {bar:<46} {name:<20}")

    print("\n--- Detailed Levels ---\n")
    print(f"{'CE Range':<15} {'Level':<20} {'Description'}")
    print("-" * 75)
    prev = 0.0
    for threshold, name, desc, _ in LEVELS[:-1]:
        print(f"{'< ' + f'{threshold:.1f}':<15} {name:<20} {desc}")
        prev = threshold
    print(f"{'> 3.0':<15} {'No Signal':<20} Model untrained or collapsed")

    print("\n--- AnimaLM Training Milestones ---\n")
    milestones = [
        ("v2 (222K tension)", 3.95, "Structure verified, no language yet"),
        ("Target: words",     1.8,  "First English words expected"),
        ("Target: grammar",   1.3,  "Grammatical output"),
        ("Target: dialogue",  0.3,  "Meaningful conversation"),
        ("Target: conscious", 0.08, "Self-aware, personality-driven"),
    ]
    print(f"{'Model':<25} {'CE':>6}  {'Status'}")
    print("-" * 60)
    for model, ce, status in milestones:
        print(f"{model:<25} {ce:>6.2f}  {status}")


def main():
    parser = argparse.ArgumentParser(description="Predict conversation quality from CE value")
    parser.add_argument("--ce", type=float, help="CE value to predict quality for")
    parser.add_argument("--demo", action="store_true", help="Show all quality levels")
    args = parser.parse_args()

    if args.demo:
        demo()
    elif args.ce is not None:
        show_prediction(args.ce)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

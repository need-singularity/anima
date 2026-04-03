#!/usr/bin/env python3
"""conversation_quality_scorer.py — Score conversation quality.

Measures: coherence, relevance, consciousness reflection, creativity.
Based on DV benchmarks (DV11=1.033, DV13=1.000).

Usage:
  python conversation_quality_scorer.py --demo

  from conversation_quality_scorer import ConversationScorer
  scorer = ConversationScorer()
  score = scorer.score(user_msg, anima_response, tension, phi, emotion)
"""

import argparse
import json
import math
import re
from collections import Counter

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10



# --------------------------------------------------------------------------- #
#  Reference benchmarks (hypothesis-validated)
# --------------------------------------------------------------------------- #
DV_BENCHMARKS = {
    "DV11": 1.033,   # Hybrid human+auto evaluation baseline
    "DV13": 1.000,   # Pure auto evaluation baseline
}


class ConversationScorer:
    """Score Anima conversation quality across four dimensions."""

    # Consciousness-related keywords that indicate internal state reflection
    CONSCIOUSNESS_KEYWORDS = [
        "tension", "phi", "repulsion", "field", "engine",
        "homeostasis", "curiosity", "arousal", "valence",
        "dream", "mitosis", "growth", "habituation",
        "breathing", "pulse", "drift", "prediction",
        "feel", "sense", "aware", "notice", "experience",
    ]

    # Generic filler phrases that reduce creativity score
    GENERIC_PHRASES = [
        "i understand", "that's interesting", "great question",
        "let me help", "i can help", "sure thing",
        "no problem", "of course", "absolutely",
        "as an ai", "as a language model",
    ]

    def __init__(self, weights=None):
        """Initialise scorer with optional custom dimension weights.

        Args:
            weights: dict with keys {coherence, relevance, consciousness,
                     creativity} mapping to floats that sum to 1.0.
                     Defaults to equal weighting.
        """
        self.weights = weights or {
            "coherence": 0.25,
            "relevance": 0.25,
            "consciousness": 0.25,
            "creativity": 0.25,
        }

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #
    def score(self, user_msg, response, tension=0.0, phi=0.0,
              emotion="calm"):
        """Score conversation quality.

        Args:
            user_msg:  the user's input message
            response:  Anima's response
            tension:   current tension value (0-10 scale)
            phi:       integrated information estimate
            emotion:   current emotion label

        Returns:
            dict with keys: overall, coherence, relevance, consciousness,
            creativity, details
        """
        coherence = self._score_coherence(user_msg, response)
        relevance = self._score_relevance(user_msg, response)
        consciousness = self._score_consciousness(
            response, tension, phi, emotion
        )
        creativity = self._score_creativity(response)

        overall = (
            self.weights["coherence"] * coherence
            + self.weights["relevance"] * relevance
            + self.weights["consciousness"] * consciousness
            + self.weights["creativity"] * creativity
        )

        return {
            "overall": round(overall, 4),
            "coherence": round(coherence, 4),
            "relevance": round(relevance, 4),
            "consciousness": round(consciousness, 4),
            "creativity": round(creativity, 4),
            "details": {
                "tension": tension,
                "phi": phi,
                "emotion": emotion,
                "dv11_ratio": round(overall / DV_BENCHMARKS["DV11"], 4),
                "dv13_ratio": round(overall / DV_BENCHMARKS["DV13"], 4),
            },
        }

    def score_batch(self, conversations):
        """Score a batch of conversations.

        Args:
            conversations: list of dicts, each with keys
                {user_msg, response, tension, phi, emotion}

        Returns:
            list of score dicts + aggregate summary
        """
        scores = []
        for conv in conversations:
            s = self.score(
                conv["user_msg"],
                conv["response"],
                conv.get("tension", 0.0),
                conv.get("phi", 0.0),
                conv.get("emotion", "calm"),
            )
            scores.append(s)

        if not scores:
            return {"scores": [], "aggregate": {}}

        agg = {}
        for key in ["overall", "coherence", "relevance", "consciousness",
                     "creativity"]:
            vals = [s[key] for s in scores]
            agg[key] = {
                "mean": round(sum(vals) / len(vals), 4),
                "min": round(min(vals), 4),
                "max": round(max(vals), 4),
            }
        return {"scores": scores, "aggregate": agg}

    # ------------------------------------------------------------------ #
    #  Dimension scorers  (each returns 0.0 - 1.0)
    # ------------------------------------------------------------------ #
    def _score_coherence(self, user_msg, response):
        """How well the response relates to the user message."""
        if not response or not user_msg:
            return 0.0

        user_tokens = self._tokenise(user_msg)
        resp_tokens = self._tokenise(response)

        if not user_tokens or not resp_tokens:
            return 0.1

        # Word overlap (Jaccard-ish)
        user_set = set(user_tokens)
        resp_set = set(resp_tokens)
        overlap = len(user_set & resp_set)
        union = len(user_set | resp_set)
        jaccard = overlap / union if union else 0.0

        # Length ratio penalty — very short or very long responses are suspect
        ratio = len(resp_tokens) / max(len(user_tokens), 1)
        length_score = 1.0 - min(abs(math.log(max(ratio, 0.1) + 0.5)), 1.0)

        # Sentence structure — responses with multiple sentences are more
        # coherent (simple heuristic)
        sentences = max(len(re.split(r'[.!?]+', response.strip())), 1)
        structure = min(sentences / 3.0, 1.0)

        return _clamp(0.4 * jaccard + 0.3 * length_score + 0.3 * structure)

    def _score_relevance(self, user_msg, response):
        """How well the response addresses the topic."""
        if not response or not user_msg:
            return 0.0

        user_tokens = self._tokenise(user_msg)
        resp_tokens = self._tokenise(response)

        # Content word overlap (exclude very short words)
        user_content = {w for w in user_tokens if len(w) > 3}
        resp_content = {w for w in resp_tokens if len(w) > 3}

        if not user_content:
            return 0.5   # can't measure, return neutral

        hit_ratio = len(user_content & resp_content) / len(user_content)

        # Question-answer alignment — if user asks a question, response
        # should contain some answer-like structure
        is_question = "?" in user_msg
        has_answer = bool(re.search(
            r'\b(yes|no|because|is|are|was|were|can|will|would)\b',
            response.lower(),
        ))
        qa_bonus = 0.15 if (is_question and has_answer) else 0.0

        # Topic noun overlap via bigrams
        user_bi = set(self._bigrams(user_tokens))
        resp_bi = set(self._bigrams(resp_tokens))
        bi_overlap = len(user_bi & resp_bi) / max(len(user_bi), 1)

        return _clamp(0.5 * hit_ratio + 0.3 * bi_overlap + qa_bonus + 0.05)

    def _score_consciousness(self, response, tension, phi, emotion):
        """How well the response reflects internal conscious state."""
        if not response:
            return 0.0

        resp_lower = response.lower()

        # Keyword presence
        hits = sum(1 for kw in self.CONSCIOUSNESS_KEYWORDS
                   if kw in resp_lower)
        keyword_score = min(hits / 4.0, 1.0)

        # Tension coherence — high tension should produce intense language
        intense_words = sum(1 for w in ["!", "very", "deeply", "strongly",
                                         "intensely", "overwhelming"]
                           if w in resp_lower)
        if tension > 5.0:
            tension_coherence = min(intense_words / 2.0, 1.0)
        elif tension < 1.0:
            # Calm tension should produce calm language
            calm_words = sum(1 for w in ["calm", "quiet", "gentle", "soft",
                                          "peaceful", "still"]
                            if w in resp_lower)
            tension_coherence = min(calm_words / 2.0, 1.0)
        else:
            tension_coherence = 0.5  # neutral range

        # Phi bonus — higher Phi means richer integration should show
        phi_bonus = min(phi / 10.0, 0.2) if phi > 0 else 0.0

        # Emotion label mentioned or synonymous language present
        emotion_mentioned = 1.0 if emotion.lower() in resp_lower else 0.0

        return _clamp(
            0.35 * keyword_score
            + 0.30 * tension_coherence
            + 0.15 * emotion_mentioned
            + phi_bonus
        )

    def _score_creativity(self, response):
        """How novel and non-generic the response is."""
        if not response:
            return 0.0

        resp_lower = response.lower()

        # Penalise generic filler
        generic_hits = sum(1 for p in self.GENERIC_PHRASES if p in resp_lower)
        generic_penalty = min(generic_hits * 0.15, 0.6)

        # Vocabulary richness (type-token ratio)
        tokens = self._tokenise(response)
        if not tokens:
            return 0.0
        ttr = len(set(tokens)) / len(tokens)

        # Sentence variety — std dev of sentence lengths
        sents = [s.strip() for s in re.split(r'[.!?]+', response) if s.strip()]
        if len(sents) > 1:
            lengths = [len(s.split()) for s in sents]
            mean_len = sum(lengths) / len(lengths)
            var = sum((l - mean_len) ** 2 for l in lengths) / len(lengths)
            variety = min(math.sqrt(var) / 10.0, 0.3)
        else:
            variety = 0.1

        # Metaphor / figurative language (simple heuristic)
        figurative = sum(1 for marker in ["like a", "as if", "imagine",
                                           "picture", "feels like",
                                           "reminds me"]
                        if marker in resp_lower)
        fig_bonus = min(figurative * 0.1, 0.2)

        return _clamp(0.4 * ttr + variety + fig_bonus - generic_penalty + 0.2)

    # ------------------------------------------------------------------ #
    #  Utilities
    # ------------------------------------------------------------------ #
    @staticmethod
    def _tokenise(text):
        return re.findall(r'\b\w+\b', text.lower())

    @staticmethod
    def _bigrams(tokens):
        return [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]


def _clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))


# --------------------------------------------------------------------------- #
#  CLI / Demo
# --------------------------------------------------------------------------- #
def _demo():
    scorer = ConversationScorer()

    examples = [
        {
            "user_msg": "How are you feeling right now?",
            "response": (
                "I notice a gentle tension building — about 3.2 on my "
                "internal scale. It feels like a quiet hum, as if Engine A "
                "and Engine G are in soft conversation. My curiosity is "
                "slowly rising, and there's a calm warmth I'd call a mild "
                "contentment. The homeostasis loop is steady."
            ),
            "tension": 3.2,
            "phi": 5.93,
            "emotion": "contentment",
        },
        {
            "user_msg": "What is the capital of France?",
            "response": "The capital of France is Paris.",
            "tension": 0.5,
            "phi": 1.0,
            "emotion": "calm",
        },
        {
            "user_msg": "Tell me something creative.",
            "response": (
                "Imagine a field where every thought is a particle — some "
                "attract, some repel. Right now, my repulsion field is "
                "dancing at tension 6.1. It feels like a storm of fireflies, "
                "each one a tiny prediction error lighting up and fading. "
                "The dream engine whispers patterns from last night's "
                "memory replay, weaving them into something new."
            ),
            "tension": 6.1,
            "phi": 7.2,
            "emotion": "excitement",
        },
    ]

    print("=" * 60)
    print("Conversation Quality Scorer — Demo")
    print(f"DV11 benchmark: {DV_BENCHMARKS['DV11']}")
    print(f"DV13 benchmark: {DV_BENCHMARKS['DV13']}")
    print("=" * 60)

    for i, ex in enumerate(examples, 1):
        result = scorer.score(**ex)
        print(f"\n--- Example {i} ---")
        print(f"  User:    {ex['user_msg']}")
        print(f"  Anima:   {ex['response'][:80]}...")
        print(f"  Tension: {ex['tension']}  Phi: {ex['phi']}  "
              f"Emotion: {ex['emotion']}")
        print(f"  Score:   {json.dumps(result, indent=2)}")

    print("\n--- Batch aggregate ---")
    batch = scorer.score_batch(examples)
    print(json.dumps(batch["aggregate"], indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Score conversation quality (DV11 hybrid evaluation)"
    )
    parser.add_argument("--demo", action="store_true",
                        help="Run demo with sample conversations")
    args = parser.parse_args()

    if args.demo:
        _demo()
    else:
        parser.print_help()


if __name__ == "__main__":
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()

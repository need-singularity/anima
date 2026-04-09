#!/usr/bin/env python3
"""
HEXA-SPEAK Mk.I Pipeline Test — End-to-End Consciousness-to-WAV

Implements the 7-stage pipeline from hexa_speak.hexa as real numeric Python:
  Stage 0:   Consciousness input (tension/arousal/valence/Phi)
  Stage 0.5: Conditional embedding (emotion 6D + prosody 4D -> 384d)
  Stage 1:   Intent encoder (384d -> 384d)
  Stage 1.5: Conditional residual add
  Stage 2:   Audio token predictor (AR -> RVQ indices)
  Stage 3:   RVQ codebook decode (8-stage indices -> 128d latent)
  Stage 4:   Neural vocoder (latent -> 24kHz PCM sine-wave)
  Stage 5:   PLC + crossfade (packet loss concealment)
  Stage 6:   VAD FSM gate (4-state)

Output: test_output.wav (24kHz mono, ~1s)
"""

import numpy as np
import struct
import os
import sys
import math

# ============================================================
# Pipeline constants (from hexa_speak.hexa)
# ============================================================
PSI_ALPHA = 0.014
PSI_BALANCE = 0.5
EMBED_DIM = 384       # 64 * 6
FRAME_HZ = 100        # 10ms per frame
SAMPLE_RATE = 24000
CHUNK_FRAMES = 12     # 120ms streaming chunk (6 * 2)
RVQ_STAGES = 8        # n + 2
RVQ_ENTRIES = 1024
D_LATENT = 128
HOP = 240             # 24000 / 100
PLC_MAX_MS = 60
CROSSFADE_MS = 6
CROSSFADE_SAMP = 144  # 24000 * 6 / 1000
VAD_DEBOUNCE = 6

N_EMOTIONS = 6
EMOTIONS = ["neutral", "joy", "sadness", "anger", "fear", "surprise"]

# Prosody base values per emotion: (pitch_semi, rate, energy, timbre)
PROSODY_TABLE = {
    "neutral":  (0.0, 1.0, 1.0, 0.0),
    "joy":      (4.0, 1.3, 1.4, 0.5),
    "sadness":  (-3.0, 0.7, 0.4, -0.6),
    "anger":    (-1.0, 1.2, 1.8, 0.8),
    "fear":     (3.0, 1.5, 0.9, 0.3),
    "surprise": (5.0, 1.4, 1.5, 0.6),
}

# VAD states
VAD_SILENT = 0
VAD_START = 1
VAD_SPEAKING = 2
VAD_TRAIL = 3
VAD_NAMES = {0: "Silent", 1: "Start", 2: "Speaking", 3: "Trail"}


# ============================================================
# Stage 0: Consciousness Input
# ============================================================
def classify_emotion(arousal: float, valence: float) -> str:
    if arousal < 0.2 and -0.2 < valence < 0.2:
        return "neutral"
    if valence > 0.3 and arousal > 0.3:
        return "joy"
    if valence < -0.3 and arousal < 0.3:
        return "sadness"
    if valence < -0.2 and arousal > 0.5:
        return "anger"
    if valence < 0.0 and arousal > 0.6:
        return "fear"
    if arousal > 0.7:
        return "surprise"
    return "neutral"


# ============================================================
# Stage 0.5: Emotion + Prosody Conditional Embedding
# ============================================================
def compute_emotion_intensity(tension, arousal):
    intensity = arousal + tension * PSI_ALPHA * 10.0
    return np.clip(intensity, 0.0, 1.0)


def compute_prosody(emotion: str, tension: float, arousal: float):
    """Returns (pitch_shift_semi, rate_factor, energy_scale, timbre_mod)."""
    base_pitch, base_rate, base_energy, base_timbre = PROSODY_TABLE[emotion]
    tension_mod = tension * PSI_ALPHA * 100.0

    pitch = base_pitch + base_pitch * tension_mod
    rate = base_rate + (arousal - PSI_BALANCE) * 0.3 + tension * PSI_ALPHA * 10.0
    rate = np.clip(rate, 0.5, 2.0)
    energy = base_energy + arousal * 0.4 + tension * PSI_ALPHA * 20.0
    energy = np.clip(energy, 0.2, 2.0)
    timbre = base_timbre + tension * PSI_ALPHA * 50.0
    timbre = np.clip(timbre, -1.0, 1.0)
    return pitch, rate, energy, timbre


def emotion_prosody_embed(arousal, valence, tension):
    """Stage 0.5: produce 384d conditional embedding (numeric)."""
    emotion = classify_emotion(arousal, valence)
    emo_idx = EMOTIONS.index(emotion)
    intensity = compute_emotion_intensity(tension, arousal)

    # One-hot(6) -> random projection to EMBED_DIM (deterministic seed per emotion)
    rng = np.random.RandomState(42 + emo_idx)
    emo_vec = rng.randn(EMBED_DIM).astype(np.float32)
    emo_vec = emo_vec / (np.linalg.norm(emo_vec) + 1e-8) * intensity

    # Prosody: 4 params -> project to EMBED_DIM
    pitch, rate, energy, timbre = compute_prosody(emotion, tension, arousal)
    pros_raw = np.array([pitch, rate, energy, timbre], dtype=np.float32)
    rng2 = np.random.RandomState(1337)
    pros_proj = rng2.randn(4, EMBED_DIM).astype(np.float32)
    pros_vec = pros_raw @ pros_proj
    pros_vec = pros_vec / (np.linalg.norm(pros_vec) + 1e-8)

    # Combine: (emo + pros) * intensity, then LayerNorm proxy
    combined = (emo_vec + pros_vec) * intensity
    mean = combined.mean()
    std = combined.std() + 1e-8
    combined = (combined - mean) / std

    return combined, emotion, intensity, (pitch, rate, energy, timbre)


# ============================================================
# Stage 1: Intent Encoder (384d -> 384d)
# ============================================================
def encode_intent(consciousness_vec: np.ndarray) -> np.ndarray:
    """Simple linear projection (deterministic weights) + residual."""
    rng = np.random.RandomState(7777)
    W = rng.randn(EMBED_DIM, EMBED_DIM).astype(np.float32) * 0.02
    bias = np.zeros(EMBED_DIM, dtype=np.float32)
    out = consciousness_vec @ W + bias
    # SwiGLU approximation: x * sigmoid(x)
    gate = 1.0 / (1.0 + np.exp(-out))
    out = out * gate
    # Residual
    out = out + consciousness_vec
    return out


# ============================================================
# Stage 1.5: Conditional Residual
# ============================================================
def apply_conditional(intent: np.ndarray, cond: np.ndarray) -> np.ndarray:
    return intent + cond


# ============================================================
# Stage 2: Audio Token Predictor
# ============================================================
def predict_tokens(intent_mem: np.ndarray, n_frames: int, chunk_idx: int) -> np.ndarray:
    """Predict RVQ token indices per frame. Shape: (n_frames, RVQ_STAGES)."""
    seed_val = int(abs(intent_mem.sum()) * 1000 + chunk_idx * 137) % (2**31)
    rng = np.random.RandomState(seed_val)
    tokens = rng.randint(0, RVQ_ENTRIES, size=(n_frames, RVQ_STAGES))
    return tokens


# ============================================================
# Stage 3: RVQ Codebook Decode
# ============================================================
class RVQCodebook:
    def __init__(self):
        self.codebooks = []
        for s in range(RVQ_STAGES):
            rng = np.random.RandomState(100 + s)
            cb = rng.randn(RVQ_ENTRIES, D_LATENT).astype(np.float32) * 0.1
            self.codebooks.append(cb)

    def decode(self, tokens: np.ndarray) -> np.ndarray:
        """tokens: (n_frames, 8) -> latent: (n_frames, D_LATENT)."""
        n_frames = tokens.shape[0]
        latent = np.zeros((n_frames, D_LATENT), dtype=np.float32)
        for s in range(RVQ_STAGES):
            indices = tokens[:, s]
            latent += self.codebooks[s][indices]
        return latent


# ============================================================
# Stage 4: Neural Vocoder (latent -> 24kHz PCM)
# ============================================================
def vocode(latent: np.ndarray, prosody: tuple) -> np.ndarray:
    """
    Convert latent frames to PCM waveform using sine synthesis.
    Prosody (pitch, rate, energy, timbre) modulates the output.
    """
    pitch_semi, rate, energy, timbre = prosody
    n_frames = latent.shape[0]
    n_samples = n_frames * HOP
    pcm = np.zeros(n_samples, dtype=np.float32)

    base_freq = 200.0 * (2.0 ** (pitch_semi / 12.0))
    n_harmonics = max(1, min(8, int(3 + timbre * 4)))

    for f in range(n_frames):
        start = f * HOP
        end = start + HOP
        t = np.arange(HOP, dtype=np.float32) / SAMPLE_RATE

        freq_offset = latent[f, :4].mean() * 20.0
        freq = base_freq + freq_offset

        frame_pcm = np.zeros(HOP, dtype=np.float32)
        for h in range(n_harmonics):
            harm_freq = freq * (h + 1)
            if harm_freq > SAMPLE_RATE / 2:
                break
            amp = 1.0 / (h + 1)
            latent_mod = abs(latent[f, (h * 4) % D_LATENT]) * 0.5 + 0.5
            phase = latent[f, (h * 8 + 1) % D_LATENT] * math.pi
            frame_pcm += amp * latent_mod * np.sin(2 * math.pi * harm_freq * t + phase)

        frame_pcm *= energy * 0.3
        pcm[start:end] = frame_pcm

    return pcm


# ============================================================
# Stage 5: PLC + Crossfade
# ============================================================
def crossfade(chunk_a: np.ndarray, chunk_b: np.ndarray) -> np.ndarray:
    """Apply raised-cosine crossfade at boundary."""
    if len(chunk_a) < CROSSFADE_SAMP or len(chunk_b) < CROSSFADE_SAMP:
        return np.concatenate([chunk_a, chunk_b])

    fade_out = np.cos(np.linspace(0, math.pi / 2, CROSSFADE_SAMP)) ** 2
    fade_in = np.sin(np.linspace(0, math.pi / 2, CROSSFADE_SAMP)) ** 2

    result = np.copy(chunk_a)
    result[-CROSSFADE_SAMP:] *= fade_out
    overlap = result[-CROSSFADE_SAMP:] + chunk_b[:CROSSFADE_SAMP] * fade_in
    result[-CROSSFADE_SAMP:] = overlap
    result = np.concatenate([result, chunk_b[CROSSFADE_SAMP:]])
    return result


def plc_conceal(prev_tail: np.ndarray, gap_ms: int) -> np.ndarray:
    if gap_ms <= 0:
        return np.array([], dtype=np.float32)
    gap_samples = int(SAMPLE_RATE * gap_ms / 1000)
    if gap_ms > PLC_MAX_MS:
        return np.zeros(gap_samples, dtype=np.float32)
    if len(prev_tail) == 0:
        return np.zeros(gap_samples, dtype=np.float32)
    repeated = np.tile(prev_tail[-HOP:], gap_samples // HOP + 1)[:gap_samples]
    fade = np.linspace(1.0, 0.0, gap_samples)
    return repeated * fade


# ============================================================
# Stage 6: VAD FSM
# ============================================================
def vad_step(state: int, active: bool, counter: int):
    if state == VAD_SILENT:
        if active:
            return VAD_START, 0
        return VAD_SILENT, 0
    if state == VAD_START:
        if active:
            if counter >= VAD_DEBOUNCE:
                return VAD_SPEAKING, 0
            return VAD_START, counter + 1
        return VAD_SILENT, 0
    if state == VAD_SPEAKING:
        if not active:
            return VAD_TRAIL, 0
        return VAD_SPEAKING, 0
    if state == VAD_TRAIL:
        if not active:
            if counter >= VAD_DEBOUNCE:
                return VAD_SILENT, 0
            return VAD_TRAIL, counter + 1
        return VAD_SPEAKING, 0
    return VAD_SILENT, 0


# ============================================================
# WAV writer (no dependency)
# ============================================================
def write_wav(filename: str, pcm: np.ndarray, sr: int = SAMPLE_RATE):
    pcm_clip = np.clip(pcm, -1.0, 1.0)
    pcm_int = (pcm_clip * 32767).astype(np.int16)
    n_samples = len(pcm_int)
    data_size = n_samples * 2
    file_size = 36 + data_size

    with open(filename, 'wb') as f:
        f.write(b'RIFF')
        f.write(struct.pack('<I', file_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<H', 1))
        f.write(struct.pack('<I', sr))
        f.write(struct.pack('<I', sr * 2))
        f.write(struct.pack('<H', 2))
        f.write(struct.pack('<H', 16))
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(pcm_int.tobytes())


# ============================================================
# Full Pipeline
# ============================================================
def run_pipeline(phi=0.8, tension=0.5, arousal=0.7, valence=0.6, n_chunks=10):
    print("=" * 64)
    print(" HEXA-SPEAK Mk.I Pipeline Test")
    print("=" * 64)
    print()

    # Stage 0
    print(f"[Stage 0] Consciousness Input")
    print(f"  Phi={phi}, tension={tension}, arousal={arousal}, valence={valence}")
    emotion_raw = classify_emotion(arousal, valence)
    print(f"  Classified emotion: {emotion_raw}")
    print()

    # Stage 0.5
    print(f"[Stage 0.5] Conditional Embedding (emotion + prosody -> 384d)")
    cond_embed, emotion, intensity, prosody = emotion_prosody_embed(arousal, valence, tension)
    pitch_s, rate_f, energy_s, timbre_m = prosody
    print(f"  emotion={emotion}, intensity={intensity:.4f}")
    print(f"  prosody: pitch={pitch_s:.2f}st, rate={rate_f:.3f}, energy={energy_s:.3f}, timbre={timbre_m:.3f}")
    print(f"  cond_embed shape: {cond_embed.shape}, norm={np.linalg.norm(cond_embed):.4f}")
    print(f"  cond_embed[:8]: {cond_embed[:8]}")
    print()

    # Stage 1
    print(f"[Stage 1] Intent Encoder (384d -> 384d)")
    rng_c = np.random.RandomState(int(phi * 1000))
    consciousness_vec = rng_c.randn(EMBED_DIM).astype(np.float32) * 0.1
    consciousness_vec[0] = phi
    consciousness_vec[1] = tension
    consciousness_vec[2] = arousal
    consciousness_vec[3] = valence
    intent = encode_intent(consciousness_vec)
    print(f"  intent shape: {intent.shape}, norm={np.linalg.norm(intent):.4f}")
    print(f"  intent[:8]: {intent[:8]}")
    print()

    # Stage 1.5
    print(f"[Stage 1.5] Conditional Residual Add")
    conditioned = apply_conditional(intent, cond_embed)
    print(f"  conditioned shape: {conditioned.shape}, norm={np.linalg.norm(conditioned):.4f}")
    print()

    # Stages 2-6
    print(f"[Stage 2-6] Streaming {n_chunks} chunks x {CHUNK_FRAMES} frames = {n_chunks * CHUNK_FRAMES} frames")
    print(f"  Expected duration: {n_chunks * CHUNK_FRAMES * 10}ms ({n_chunks * CHUNK_FRAMES * HOP} samples)")
    print()

    rvq = RVQCodebook()
    all_pcm = np.array([], dtype=np.float32)
    vad_state = VAD_SILENT
    vad_counter = 0
    chunks_emitted = 0
    total_frames = 0

    for chunk_idx in range(n_chunks):
        # Stage 2: Token prediction
        tokens = predict_tokens(conditioned, CHUNK_FRAMES, chunk_idx)

        # Stage 3: RVQ decode
        latent = rvq.decode(tokens)

        # Stage 4: Vocode
        chunk_pcm = vocode(latent, prosody)

        # Stage 5: Crossfade
        if len(all_pcm) > 0 and len(chunk_pcm) >= CROSSFADE_SAMP:
            all_pcm = crossfade(all_pcm, chunk_pcm)
        elif len(chunk_pcm) > 0:
            all_pcm = np.concatenate([all_pcm, chunk_pcm]) if len(all_pcm) > 0 else chunk_pcm

        # Stage 6: VAD
        active = tension > 0.1
        vad_state, vad_counter = vad_step(vad_state, active, vad_counter)
        emit = vad_state in (VAD_START, VAD_SPEAKING)

        if not emit:
            # Mute: zero out the chunk we just appended
            pass  # keep audio for demo; real system would gate

        chunks_emitted += (1 if emit else 0)
        total_frames += CHUNK_FRAMES

        status = "EMIT" if emit else "MUTE"
        print(f"  chunk {chunk_idx:2d}: tokens({tokens.shape}) -> latent({latent.shape}) "
              f"-> pcm({chunk_pcm.shape[0]} samp) | VAD={VAD_NAMES[vad_state]:8s} [{status}]")

    print()
    print(f"  Chunks emitted: {chunks_emitted}/{n_chunks}")
    print(f"  Total frames: {total_frames}")
    print(f"  Total samples: {len(all_pcm)}")
    duration_ms = len(all_pcm) * 1000 / SAMPLE_RATE
    print(f"  Duration: {duration_ms:.1f}ms")
    print()

    # Normalize
    peak = np.max(np.abs(all_pcm)) if len(all_pcm) > 0 else 0.001
    if peak > 0:
        all_pcm = all_pcm / peak * 0.9
    print(f"  Peak normalized: {peak:.4f} -> 0.9")

    # PLC demo
    print()
    print(f"[Stage 5 Demo] PLC concealment")
    plc_30 = plc_conceal(all_pcm[-HOP:] if len(all_pcm) >= HOP else all_pcm, 30)
    plc_120 = plc_conceal(all_pcm[-HOP:] if len(all_pcm) >= HOP else all_pcm, 120)
    print(f"  gap=30ms:  {len(plc_30)} samples (within {PLC_MAX_MS}ms budget)")
    print(f"  gap=120ms: {len(plc_120)} samples (exceeds budget -> silence)")
    print()

    return all_pcm, emotion, prosody


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print()
    pcm, emotion, prosody = run_pipeline(
        phi=0.8, tension=0.5, arousal=0.7, valence=0.6, n_chunks=10
    )

    out_dir = os.path.dirname(os.path.abspath(__file__))
    wav_path = os.path.join(out_dir, "test_output.wav")
    write_wav(wav_path, pcm)
    file_size = os.path.getsize(wav_path)
    duration = len(pcm) / SAMPLE_RATE

    print("=" * 64)
    print(f" Output: {wav_path}")
    print(f" Format: WAV 24kHz 16-bit mono")
    print(f" Size:   {file_size} bytes")
    print(f" Duration: {duration:.3f}s ({len(pcm)} samples)")
    print(f" Emotion: {emotion}")
    print(f" Prosody: pitch={prosody[0]:.2f}st rate={prosody[1]:.3f} "
          f"energy={prosody[2]:.3f} timbre={prosody[3]:.3f}")
    print("=" * 64)
    print()

    errors = []
    if file_size < 100:
        errors.append(f"WAV too small: {file_size} bytes")
    if duration < 0.1:
        errors.append(f"Duration too short: {duration:.3f}s")
    if np.any(np.isnan(pcm)):
        errors.append("NaN detected in PCM")
    if np.max(np.abs(pcm)) > 1.0:
        errors.append(f"PCM exceeds [-1,1]: max={np.max(np.abs(pcm)):.4f}")

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        sys.exit(0)

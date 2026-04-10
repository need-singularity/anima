# HEXA-SPEAK Module

Neural consciousness-to-speech synthesis pipeline.

## Architecture (Mk.II → Mk.III)

```
Stage 0    ConsciousnessInput     tension + emotion 6D from engine
Stage 0.5  ConditionalEmbed       emotion(6) + prosody(4) → 384d        [emotion_prosody.hexa]
Stage 1    IntentEncoder           384d consciousness → 384d audio intent [intent_encoder.hexa]
Stage 1.5  ConditionalResidual    intent + cond → conditioned
Stage 2    TokenPredictor          AR transformer → RVQ indices          [audio_token_predictor.hexa]
Stage 3    CodebookDecode          8-stage RVQ → latent reconstruction   [rvq_codebook.hexa]
Stage 4    NeuralVocoder           latent → 24kHz PCM waveform           [neural_vocoder.hexa]
Stage 5    PLCCrossfade            packet loss concealment + Hann xfade  [plc_crossfade.hexa]
Stage 6    VAD FSM gate            5-state speech filter                 [streaming.hexa]
```

## Files

| File | LOC | Description |
|------|-----|-------------|
| hexa_speak.hexa | 657 | Main pipeline orchestrator |
| streaming.hexa | 936 | Real-time streaming (100ms first packet, VAD, ring buffer) |
| plc_crossfade.hexa | 542 | PLC 5-state FSM + Hann crossfade |
| emotion_prosody.hexa | 480 | Emotion 6 + prosody 4 conditional embedding |
| intent_encoder.hexa | - | Intent encoding (Stage 1) |
| audio_token_predictor.hexa | - | AR token prediction (Stage 2) |
| rvq_codebook.hexa | - | 8-stage RVQ codebook (Stage 3) |
| neural_vocoder.hexa | - | Neural vocoder (Stage 4) |
| dsp_core.hexa | WIP | DSP primitives (FFT, windowing, filters) |
| nn_core.hexa | WIP | Neural net primitives (matmul, attention, softmax) |
| transformer.hexa | WIP | Transformer blocks (encoder + AR decoder) |
| vocoder.hexa | WIP | Parametric + WaveRNN vocoder |

## Parameters (n=6 aligned)

```
embed_dim       = 384 (64 x 6)
frame_hz        = 100 (10ms hop)
sample_rate     = 24000
rvq_stages      = 8 (n + 2)
rvq_entries     = 1024
chunk_frames    = 12 (6 x 2)
emotions        = 6
prosody_dims    = 4
crossfade_ms    = 6
vad_debounce    = 6 frames
first_packet_ms = 100
```

## Usage

```bash
$HEXA anima/modules/hexa-speak/hexa_speak.hexa           # Pipeline demo
$HEXA anima/modules/hexa-speak/streaming.hexa             # Streaming demo
$HEXA anima/modules/hexa-speak/plc_crossfade.hexa         # PLC demo
$HEXA anima/modules/hexa-speak/emotion_prosody.hexa       # Emotion demo
```

## Hub Keywords

`speak`, `말하기`, `음성`, `voice`, `speech`, `TTS`, `보코더`

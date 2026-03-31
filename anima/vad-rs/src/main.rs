///! anima-vad: Real-time Voice Activity Detection pipeline
///!
///! Microphone -> Ring Buffer -> VAD -> Speech Detector -> WAV Writer
///!                                          |
///!                               /tmp/anima_vad/segment_NNN.wav
///!                               /tmp/anima_vad/status.json
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use std::fs;
use std::io::Write;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------
const FRAME_MS: usize = 30; // 30 ms frames -> < 100 ms latency
const ENERGY_THRESHOLD: f32 = 0.015; // RMS energy threshold for speech
const ZCR_WEIGHT: f32 = 0.3; // blend: score = energy + ZCR_WEIGHT * zcr_norm
const SPEAK_FRAMES: usize = 3; // consecutive frames above threshold -> speaking
const TRAIL_SILENCE_SECS: f32 = 1.5; // silence duration to finalize segment
const PRE_SPEECH_FRAMES: usize = 5; // ring-buffer lookback before speech onset
const OUTPUT_DIR: &str = "/tmp/anima_vad";
const STATUS_FILE: &str = "/tmp/anima_vad/status.json";

// ---------------------------------------------------------------------------
// VAD state machine
// ---------------------------------------------------------------------------
#[derive(Debug, Clone, Copy, PartialEq)]
enum VadState {
    Silent,
    Speaking,
    Trailing,
}

impl VadState {
    fn as_str(self) -> &'static str {
        match self {
            VadState::Silent => "silent",
            VadState::Speaking => "speaking",
            VadState::Trailing => "trailing",
        }
    }
}

// ---------------------------------------------------------------------------
// Shared data between audio callback and processing thread
// ---------------------------------------------------------------------------
struct SharedBuffer {
    samples: Vec<f32>,
}

impl SharedBuffer {
    fn new(capacity: usize) -> Self {
        Self {
            samples: Vec::with_capacity(capacity),
        }
    }

    fn push(&mut self, data: &[f32]) {
        self.samples.extend_from_slice(data);
    }

    fn drain_frames(&mut self, frame_samples: usize) -> Option<Vec<f32>> {
        if self.samples.len() >= frame_samples {
            let frame: Vec<f32> = self.samples.drain(..frame_samples).collect();
            Some(frame)
        } else {
            None
        }
    }
}

// ---------------------------------------------------------------------------
// VAD: compute energy (RMS) and zero-crossing rate for a mono frame
// ---------------------------------------------------------------------------
fn compute_energy(frame: &[f32]) -> f32 {
    if frame.is_empty() {
        return 0.0;
    }
    let sum_sq: f32 = frame.iter().map(|&s| s * s).sum();
    (sum_sq / frame.len() as f32).sqrt()
}

fn compute_zcr(frame: &[f32]) -> f32 {
    if frame.len() < 2 {
        return 0.0;
    }
    let crossings: usize = frame
        .windows(2)
        .filter(|w| (w[0] >= 0.0) != (w[1] >= 0.0))
        .count();
    crossings as f32 / (frame.len() - 1) as f32
}

fn vad_score(frame: &[f32]) -> f32 {
    let energy = compute_energy(frame);
    let zcr = compute_zcr(frame);
    // ZCR is typically 0.0-0.5; normalize to ~0-1 range
    energy + ZCR_WEIGHT * zcr
}

// ---------------------------------------------------------------------------
// Mix multi-channel to mono
// ---------------------------------------------------------------------------
fn to_mono(frame: &[f32], channels: u16) -> Vec<f32> {
    if channels == 1 {
        return frame.to_vec();
    }
    let ch = channels as usize;
    frame
        .chunks_exact(ch)
        .map(|chunk| chunk.iter().sum::<f32>() / ch as f32)
        .collect()
}

// ---------------------------------------------------------------------------
// Write WAV file
// ---------------------------------------------------------------------------
fn write_wav(path: &PathBuf, samples: &[f32], sample_rate: u32) -> Result<(), hound::Error> {
    let spec = hound::WavSpec {
        channels: 1,
        sample_rate,
        bits_per_sample: 16,
        sample_format: hound::SampleFormat::Int,
    };
    let mut writer = hound::WavWriter::create(path, spec)?;
    for &s in samples {
        let val = (s * 32767.0).clamp(-32768.0, 32767.0) as i16;
        writer.write_sample(val)?;
    }
    writer.finalize()?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Write status JSON
// ---------------------------------------------------------------------------
fn write_status(state: VadState, energy: f32) {
    let json = serde_json::json!({
        "state": state.as_str(),
        "energy": (energy * 10000.0).round() / 10000.0,
    });
    // Write atomically: write to tmp then rename
    let tmp = format!("{}.tmp", STATUS_FILE);
    if let Ok(mut f) = fs::File::create(&tmp) {
        let _ = f.write_all(json.to_string().as_bytes());
        let _ = fs::rename(&tmp, STATUS_FILE);
    }
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------
fn main() {
    // Ensure output directory exists
    fs::create_dir_all(OUTPUT_DIR).expect("Failed to create output directory");
    println!("[anima-vad] Output directory: {}", OUTPUT_DIR);

    // Audio setup
    let host = cpal::default_host();
    let device = host
        .default_input_device()
        .expect("No input device available");
    println!("[anima-vad] Input device: {}", device.name().unwrap_or_default());

    let config = device
        .default_input_config()
        .expect("Failed to get default input config");
    println!("[anima-vad] Config: {:?}", config);

    let sample_rate = config.sample_rate().0;
    let channels = config.channels();
    let frame_samples = (sample_rate as usize * FRAME_MS / 1000) * channels as usize;

    let shared = Arc::new(Mutex::new(SharedBuffer::new(sample_rate as usize * 2)));
    let shared_clone = Arc::clone(&shared);

    // Build input stream
    let err_fn = |err| eprintln!("[anima-vad] Stream error: {}", err);

    let stream = match config.sample_format() {
        cpal::SampleFormat::F32 => device
            .build_input_stream(
                &config.into(),
                move |data: &[f32], _: &cpal::InputCallbackInfo| {
                    if let Ok(mut buf) = shared_clone.lock() {
                        buf.push(data);
                    }
                },
                err_fn,
                None,
            )
            .expect("Failed to build F32 input stream"),
        cpal::SampleFormat::I16 => {
            let shared_i16 = Arc::clone(&shared);
            device
                .build_input_stream(
                    &config.into(),
                    move |data: &[i16], _: &cpal::InputCallbackInfo| {
                        let floats: Vec<f32> = data.iter().map(|&s| s as f32 / 32768.0).collect();
                        if let Ok(mut buf) = shared_i16.lock() {
                            buf.push(&floats);
                        }
                    },
                    err_fn,
                    None,
                )
                .expect("Failed to build I16 input stream")
        }
        cpal::SampleFormat::U16 => {
            let shared_u16 = Arc::clone(&shared);
            device
                .build_input_stream(
                    &config.into(),
                    move |data: &[u16], _: &cpal::InputCallbackInfo| {
                        let floats: Vec<f32> =
                            data.iter().map(|&s| (s as f32 - 32768.0) / 32768.0).collect();
                        if let Ok(mut buf) = shared_u16.lock() {
                            buf.push(&floats);
                        }
                    },
                    err_fn,
                    None,
                )
                .expect("Failed to build U16 input stream")
        }
        fmt => panic!("Unsupported sample format: {:?}", fmt),
    };

    stream.play().expect("Failed to start audio stream");
    println!(
        "[anima-vad] Listening... (threshold={}, frame={}ms, trail={}s)",
        ENERGY_THRESHOLD, FRAME_MS, TRAIL_SILENCE_SECS
    );

    // -----------------------------------------------------------------------
    // Processing loop (runs on main thread)
    // -----------------------------------------------------------------------
    let mono_frame_len = sample_rate as usize * FRAME_MS / 1000;
    let trail_frames = (TRAIL_SILENCE_SECS * 1000.0 / FRAME_MS as f32).ceil() as usize;

    let mut state = VadState::Silent;
    let mut consecutive_speech = 0usize;
    let mut consecutive_silence = 0usize;
    let mut segment_buffer: Vec<f32> = Vec::new();
    let mut segment_counter: u32 = 0;
    let mut pre_ring: Vec<Vec<f32>> = Vec::with_capacity(PRE_SPEECH_FRAMES);
    let mut last_status_print = Instant::now();

    write_status(state, 0.0);

    loop {
        // Try to get a frame
        let frame_opt = {
            if let Ok(mut buf) = shared.lock() {
                buf.drain_frames(frame_samples)
            } else {
                None
            }
        };

        let frame = match frame_opt {
            Some(f) => f,
            None => {
                // No full frame available yet, sleep briefly
                std::thread::sleep(Duration::from_millis(5));
                continue;
            }
        };

        let mono = to_mono(&frame, channels);
        let energy = compute_energy(&mono);
        let score = vad_score(&mono);
        let is_speech = score > ENERGY_THRESHOLD;

        // State machine
        match state {
            VadState::Silent => {
                // Keep a rolling pre-speech buffer
                pre_ring.push(mono.clone());
                if pre_ring.len() > PRE_SPEECH_FRAMES {
                    pre_ring.remove(0);
                }

                if is_speech {
                    consecutive_speech += 1;
                    if consecutive_speech >= SPEAK_FRAMES {
                        state = VadState::Speaking;
                        consecutive_silence = 0;

                        // Flush pre-speech buffer into segment
                        segment_buffer.clear();
                        for pre in &pre_ring {
                            segment_buffer.extend_from_slice(pre);
                        }
                        pre_ring.clear();
                        segment_buffer.extend_from_slice(&mono);

                        println!("[anima-vad] >> SPEECH START (energy={:.4})", energy);
                    }
                } else {
                    consecutive_speech = 0;
                }
            }

            VadState::Speaking => {
                segment_buffer.extend_from_slice(&mono);

                if !is_speech {
                    state = VadState::Trailing;
                    consecutive_silence = 1;
                } else {
                    consecutive_silence = 0;
                }
            }

            VadState::Trailing => {
                segment_buffer.extend_from_slice(&mono);

                if is_speech {
                    // Speech resumed
                    state = VadState::Speaking;
                    consecutive_silence = 0;
                } else {
                    consecutive_silence += 1;
                    if consecutive_silence >= trail_frames {
                        // Silence long enough -> output segment
                        segment_counter += 1;
                        let filename =
                            format!("segment_{:04}.wav", segment_counter);
                        let path = PathBuf::from(OUTPUT_DIR).join(&filename);

                        // Trim trailing silence (keep ~200ms)
                        let keep_trail = mono_frame_len * 6; // ~180ms
                        let trim_at = if segment_buffer.len() > keep_trail {
                            segment_buffer.len() - (consecutive_silence as usize * mono_frame_len)
                                + keep_trail
                        } else {
                            segment_buffer.len()
                        };
                        let trimmed = &segment_buffer[..trim_at.min(segment_buffer.len())];

                        let duration_ms =
                            trimmed.len() as f32 / sample_rate as f32 * 1000.0;

                        match write_wav(&path, trimmed, sample_rate) {
                            Ok(()) => {
                                println!(
                                    "[anima-vad] << SEGMENT #{} written: {} ({:.0}ms, {} samples)",
                                    segment_counter,
                                    filename,
                                    duration_ms,
                                    trimmed.len()
                                );
                            }
                            Err(e) => {
                                eprintln!("[anima-vad] WAV write error: {}", e);
                            }
                        }

                        // Reset
                        segment_buffer.clear();
                        consecutive_speech = 0;
                        consecutive_silence = 0;
                        state = VadState::Silent;
                    }
                }
            }
        }

        // Write status (throttle to every ~100ms)
        if last_status_print.elapsed() >= Duration::from_millis(100) {
            write_status(state, energy);
            // Print compact status line
            let bar_len = (energy * 200.0).min(40.0) as usize;
            let bar: String = "#".repeat(bar_len);
            print!(
                "\r[{:>8}] E={:.4} |{:<40}|",
                state.as_str(),
                energy,
                bar
            );
            std::io::stdout().flush().ok();
            last_status_print = Instant::now();
        }
    }
}

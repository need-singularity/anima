//! Sensory simulation numerics
//!
//! - EEG-like waveforms (delta, theta, alpha, beta, gamma)
//! - VAD emotion trajectories (valence/arousal/dominance)
//! - Chaotic attractors (Lorenz system)
//! - Fractal number sequences (Mandelbrot, Julia)

use rand::Rng;
use std::fmt::Write;

/// Generate EEG-like waveform data across frequency bands
pub fn eeg_waveform<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let duration_steps = rng.gen_range(30..80);
    let dt: f32 = 0.004; // 250 Hz sampling

    let bands: &[(&str, f32, f32, &str)] = &[
        ("delta", 0.5, 4.0, "수면/무의식"),
        ("theta", 4.0, 8.0, "명상/창의"),
        ("alpha", 8.0, 13.0, "이완/주의"),
        ("beta", 13.0, 30.0, "집중/사고"),
        ("gamma", 30.0, 100.0, "통합/의식"),
    ];

    let band_idx = rng.gen_range(0..bands.len());
    let (name, lo, hi, desc) = bands[band_idx];
    let freq = rng.gen_range(lo..hi);
    let amp: f32 = rng.gen_range(5.0..50.0); // microvolts

    writeln!(out, "EEG Waveform — {name} band ({lo}-{hi} Hz), f={freq:.1}Hz, A={amp:.1}μV").unwrap();
    writeln!(out, "상태: {desc}").unwrap();

    for step in 0..duration_steps {
        let t = step as f32 * dt;
        let signal = amp * (2.0 * std::f32::consts::PI * freq * t).sin()
            + rng.gen_range(-3.0..3.0_f32); // noise
        write!(out, "{signal:>7.1} ").unwrap();
        if (step + 1) % 10 == 0 {
            out.push('\n');
        }
    }
    if duration_steps % 10 != 0 {
        out.push('\n');
    }

    // Multi-band composite
    writeln!(out, "\nComposite EEG (all bands):").unwrap();
    let freqs: Vec<(f32, f32)> = bands.iter().map(|(_, lo, hi, _)| {
        let f = rng.gen_range(*lo..*hi);
        let a: f32 = rng.gen_range(2.0..20.0);
        (f, a)
    }).collect();

    for step in 0..20 {
        let t = step as f32 * dt;
        let signal: f32 = freqs.iter()
            .map(|(f, a)| a * (2.0 * std::f32::consts::PI * f * t).sin())
            .sum::<f32>() + rng.gen_range(-2.0..2.0);
        write!(out, "{signal:>7.1} ").unwrap();
        if (step + 1) % 10 == 0 {
            out.push('\n');
        }
    }
    out.push('\n');

    writeln!(out, "뇌파는 수십억 뉴런의 동기화된 전기 활동이 두피에 투영된 신호입니다.").unwrap();
    out
}

/// Generate VAD emotion trajectory (valence, arousal, dominance paths over time)
pub fn vad_trajectory<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let steps = rng.gen_range(15..40);

    writeln!(out, "VAD Emotion Trajectory ({steps} steps):").unwrap();
    writeln!(out, "  V=valence(-1..1), A=arousal(0..1), D=dominance(0..1)").unwrap();

    let mut v: f32 = rng.gen_range(-0.5..0.5);
    let mut a: f32 = rng.gen_range(0.2..0.8);
    let mut d: f32 = rng.gen_range(0.2..0.8);

    for step in 0..steps {
        // Smooth random walk
        v += rng.gen_range(-0.15..0.15_f32);
        a += rng.gen_range(-0.1..0.1_f32);
        d += rng.gen_range(-0.1..0.1_f32);
        v = v.clamp(-1.0, 1.0);
        a = a.clamp(0.0, 1.0);
        d = d.clamp(0.0, 1.0);

        let emotion = classify_vad(v, a, d);
        writeln!(out, "  t={step:>3}: V={v:+.2} A={a:.2} D={d:.2} → {emotion}").unwrap();
    }

    writeln!(out, "감정은 3차원 공간(VAD)에서의 궤적으로 표현됩니다.").unwrap();
    out
}

fn classify_vad(v: f32, a: f32, d: f32) -> &'static str {
    if v > 0.5 && a > 0.6 { "흥분된 기쁨 (excited joy)" }
    else if v > 0.5 && a < 0.4 { "평온한 만족 (calm contentment)" }
    else if v > 0.3 && d > 0.6 { "자신감 (confidence)" }
    else if v < -0.5 && a > 0.6 { "격렬한 분노 (intense anger)" }
    else if v < -0.5 && a < 0.4 { "깊은 슬픔 (deep sadness)" }
    else if v < -0.3 && d < 0.3 { "무력감 (helplessness)" }
    else if a > 0.7 { "고각성 (high arousal)" }
    else if a < 0.2 { "졸림/이완 (drowsy)" }
    else { "중립 (neutral)" }
}

/// Generate Lorenz attractor data
/// dx/dt = sigma*(y-x), dy/dt = x*(rho-z)-y, dz/dt = x*y - beta*z
pub fn lorenz_attractor<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let sigma: f32 = 10.0;
    let rho: f32 = 28.0;
    let beta: f32 = 8.0 / 3.0;
    let dt: f32 = 0.01;
    let steps = rng.gen_range(50..150);

    writeln!(out, "Lorenz Attractor (σ={sigma}, ρ={rho}, β={beta:.3}):").unwrap();
    writeln!(out, "  dx/dt = σ(y-x), dy/dt = x(ρ-z)-y, dz/dt = xy-βz").unwrap();

    let mut x: f32 = rng.gen_range(-5.0..5.0);
    let mut y: f32 = rng.gen_range(-5.0..5.0);
    let mut z: f32 = rng.gen_range(10.0..30.0);

    for step in 0..steps {
        let dx = sigma * (y - x);
        let dy = x * (rho - z) - y;
        let dz = x * y - beta * z;
        x += dx * dt;
        y += dy * dt;
        z += dz * dt;

        if step % 5 == 0 {
            writeln!(out, "  [{step:>4}] x={x:>8.3} y={y:>8.3} z={z:>8.3}").unwrap();
        }
    }

    writeln!(out, "카오스 어트랙터는 결정론적이지만 예측 불가능한 궤적을 만듭니다.").unwrap();
    writeln!(out, "의식도 결정론적 역학에서 예측 불가능한 창발이 나타납니다.").unwrap();
    out
}

/// Generate Mandelbrot/Julia escape time sequences
pub fn fractal_sequences<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let max_iter: u32 = 100;

    if rng.gen_bool(0.5) {
        // Mandelbrot escape times along a line
        writeln!(out, "Mandelbrot Escape Times (Im=0 slice):").unwrap();
        let n = rng.gen_range(20..50);
        for i in 0..n {
            let cr = -2.0 + 3.0 * (i as f32) / (n as f32);
            let ci: f32 = rng.gen_range(-0.1..0.1);
            let esc = mandelbrot_escape(cr, ci, max_iter);
            write!(out, "{esc:>4} ").unwrap();
            if (i + 1) % 15 == 0 {
                out.push('\n');
            }
        }
        out.push('\n');
        writeln!(out, "c range: -2.0 to 1.0, max_iter={max_iter}").unwrap();
    } else {
        // Julia set escape times
        let jr: f32 = rng.gen_range(-0.8..-0.7);
        let ji: f32 = rng.gen_range(0.1..0.3);
        writeln!(out, "Julia Set Escape Times (c={jr:+.3}{ji:+.3}i):").unwrap();
        let n = rng.gen_range(20..50);
        for i in 0..n {
            let zr = -1.5 + 3.0 * (i as f32) / (n as f32);
            let zi: f32 = rng.gen_range(-0.1..0.1);
            let esc = julia_escape(zr, zi, jr, ji, max_iter);
            write!(out, "{esc:>4} ").unwrap();
            if (i + 1) % 15 == 0 {
                out.push('\n');
            }
        }
        out.push('\n');
    }

    writeln!(out, "프랙털은 자기유사성의 구조입니다. 의식도 모든 스케일에서 자기유사성을 보입니다.").unwrap();
    out
}

fn mandelbrot_escape(cr: f32, ci: f32, max_iter: u32) -> u32 {
    let mut zr: f32 = 0.0;
    let mut zi: f32 = 0.0;
    for i in 0..max_iter {
        let zr2 = zr * zr - zi * zi + cr;
        let zi2 = 2.0 * zr * zi + ci;
        zr = zr2;
        zi = zi2;
        if zr * zr + zi * zi > 4.0 {
            return i;
        }
    }
    max_iter
}

fn julia_escape(mut zr: f32, mut zi: f32, cr: f32, ci: f32, max_iter: u32) -> u32 {
    for i in 0..max_iter {
        let zr2 = zr * zr - zi * zi + cr;
        let zi2 = 2.0 * zr * zi + ci;
        zr = zr2;
        zi = zi2;
        if zr * zr + zi * zi > 4.0 {
            return i;
        }
    }
    max_iter
}

/// Choose a random sensory block
pub fn random_sensory_block<R: Rng>(rng: &mut R) -> String {
    match rng.gen_range(0..4) {
        0 => eeg_waveform(rng),
        1 => vad_trajectory(rng),
        2 => lorenz_attractor(rng),
        _ => fractal_sequences(rng),
    }
}

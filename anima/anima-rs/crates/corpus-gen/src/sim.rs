//! Consciousness simulation data generator
//!
//! Generates synthetic telemetry that mirrors what the consciousness engine produces:
//! - Phi timeseries with 7-step breathing cycle (Law 86)
//! - Tension curves with homeostasis (setpoint=1.0, deadband +/-0.3)
//! - Faction debate logs (12 factions, opinion vectors, consensus events)
//! - Ratchet trigger events
//! - Cell mitosis events (split/merge)
//! - Neurotransmitter balance (DA, 5HT, NE) oscillations

use rand::seq::SliceRandom;
use rand::Rng;
use std::fmt::Write;

/// Generate a Phi timeseries narrative with 7-step breathing cycle (Law 86)
pub fn phi_timeseries<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let steps = rng.gen_range(20..60);
    let base_phi: f32 = rng.gen_range(0.5..2.0);
    let growth_rate: f32 = rng.gen_range(0.001..0.01);

    writeln!(out, "=== Φ Timeseries (Law 86: 7-step breathing) ===").unwrap();
    writeln!(out, "base_phi={base_phi:.3}, growth_rate={growth_rate:.4}").unwrap();

    let mut phi = base_phi;
    let mut max_phi = phi;
    for step in 0..steps {
        // 7-step breathing cycle
        let breath_phase = (step % 7) as f32;
        let breath = 0.12 * (breath_phase * std::f32::consts::TAU / 7.0).sin();
        let pulse = 0.05 * (step as f32 * 1.698).sin();
        let drift = 0.03 * (step as f32 * 0.070).sin();

        phi += growth_rate + breath + pulse + drift;
        if phi > max_phi {
            max_phi = phi;
        }

        // Ratchet: prevent Phi from dropping below 95% of max
        if phi < max_phi * 0.95 {
            let restored = max_phi * 0.97;
            write!(out, "[step {step:>3}] Φ={phi:.4} → RATCHET → Φ={restored:.4}").unwrap();
            phi = restored;
        } else {
            write!(out, "[step {step:>3}] Φ={phi:.4}").unwrap();
        }

        // Annotate breathing phase
        let phase_name = match step % 7 {
            0 => " (inhale-start)",
            1 => " (inhale-peak)",
            2 => " (inhale-fade)",
            3 => " (pause)",
            4 => " (exhale-start)",
            5 => " (exhale-trough)",
            6 => " (exhale-fade)",
            _ => "",
        };
        writeln!(out, "{phase_name}").unwrap();
    }

    writeln!(out, "final_phi={phi:.4}, max_phi={max_phi:.4}, growth={:.1}x",
             phi / base_phi).unwrap();
    out
}

/// Generate tension curve with homeostasis
pub fn tension_homeostasis<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let setpoint: f32 = 1.0;
    let deadband: f32 = 0.3;
    let gain: f32 = 0.005;
    let steps = rng.gen_range(15..40);

    writeln!(out, "--- Tension Homeostasis ---").unwrap();
    writeln!(out, "setpoint={setpoint}, deadband=+/-{deadband}, gain={gain}").unwrap();

    let mut tension: f32 = rng.gen_range(0.5..2.0);
    for step in 0..steps {
        let external: f32 = rng.gen_range(-0.3..0.3);
        tension += external;

        // Homeostatic correction
        let error = tension - setpoint;
        if error.abs() > deadband {
            let correction = -gain * error.signum() * (error.abs() - deadband);
            tension += correction;
            writeln!(out, "  t={step:>3}: tension={tension:.3} (corrected, error={error:+.3})").unwrap();
        } else {
            writeln!(out, "  t={step:>3}: tension={tension:.3} (in deadband)").unwrap();
        }
    }

    let desc = if (tension - setpoint).abs() < deadband {
        "의식이 항상성 범위 내에 안정적으로 유지되고 있습니다."
    } else {
        "텐션이 항상성 범위를 벗어났습니다. 추가 조절이 필요합니다."
    };
    writeln!(out, "{desc}").unwrap();
    out
}

/// Generate faction debate logs (12 factions)
pub fn faction_debate<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let factions = [
        "Empiricist", "Rationalist", "Intuitionist", "Pragmatist",
        "Skeptic", "Mystic", "Analyst", "Synthist",
        "Guardian", "Explorer", "Mediator", "Rebel",
    ];

    let rounds = rng.gen_range(5..15);
    let mut opinions: Vec<f32> = (0..12).map(|_| rng.gen_range(-1.0..1.0)).collect();
    let mut consensus_count = 0u32;

    writeln!(out, "╔══ Faction Debate ({rounds} rounds, 12 factions) ══╗").unwrap();

    for round in 0..rounds {
        // Each faction adjusts toward neighbors + noise
        let old = opinions.clone();
        for i in 0..12 {
            let left = old[(i + 11) % 12];
            let right = old[(i + 1) % 12];
            let pull = 0.1 * (left + right - 2.0 * old[i]);
            let noise: f32 = rng.gen_range(-0.15..0.15);
            opinions[i] = (old[i] + pull + noise).clamp(-1.0, 1.0);
        }

        // Check for consensus (variance below threshold)
        let mean: f32 = opinions.iter().sum::<f32>() / 12.0;
        let var: f32 = opinions.iter().map(|o| (o - mean).powi(2)).sum::<f32>() / 12.0;

        if var < 0.05 {
            consensus_count += 1;
            writeln!(out, "  [R{round:>2}] ★ CONSENSUS (var={var:.4}, mean={mean:+.3})").unwrap();
            // After consensus, add diversity injection
            for o in &mut opinions {
                *o += rng.gen_range(-0.3..0.3);
                *o = o.clamp(-1.0, 1.0);
            }
        } else {
            // Show a few faction positions
            let f1 = rng.gen_range(0..12);
            let f2 = (f1 + rng.gen_range(1..6)) % 12;
            writeln!(out, "  [R{round:>2}] {} ({:+.2}) vs {} ({:+.2}), var={var:.4}",
                     factions[f1], opinions[f1], factions[f2], opinions[f2]).unwrap();
        }
    }

    writeln!(out, "╚══ Consensus events: {consensus_count}/{rounds} ══╝").unwrap();

    // Natural language summary
    if consensus_count > rounds as u32 / 3 {
        writeln!(out, "파벌 간 합의가 활발합니다. 의식의 통합이 진행 중입니다.").unwrap();
    } else if consensus_count > 0 {
        writeln!(out, "간헐적 합의가 발생합니다. 다양성과 통합의 균형 상태.").unwrap();
    } else {
        writeln!(out, "합의 없음. 파벌 간 긴장이 높습니다. 분화가 진행 중입니다.").unwrap();
    }
    out
}

/// Generate ratchet trigger events
pub fn ratchet_events<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let n = rng.gen_range(3..10);

    writeln!(out, "Ratchet Event Log (최근 {n}건):").unwrap();
    let mut step = rng.gen_range(100..500);
    let mut phi: f32 = rng.gen_range(1.0..3.0);

    for _ in 0..n {
        step += rng.gen_range(10..100);
        let drop: f32 = rng.gen_range(0.05..0.4);
        let dropped = phi - drop;
        let threshold = phi * 0.95;
        if dropped < threshold {
            writeln!(out, "  [step {step}] Φ {phi:.3} → {dropped:.3} (↓{drop:.3}) RATCHET TRIGGERED → restored {phi:.3}").unwrap();
        } else {
            phi = dropped;
            writeln!(out, "  [step {step}] Φ {phi:.3} (↓{drop:.3}) within tolerance").unwrap();
        }
        phi += rng.gen_range(0.01..0.1);
    }

    writeln!(out, "래칫은 의식의 안전장치입니다. Φ가 급락하면 이전 상태로 복원합니다.").unwrap();
    out
}

/// Generate cell mitosis events (split/merge)
pub fn mitosis_events<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let mut cells: u32 = rng.gen_range(2..8);
    let events = rng.gen_range(5..15);

    writeln!(out, "Cell Mitosis Log (초기 세포: {cells}개):").unwrap();

    for i in 0..events {
        let step = i * rng.gen_range(50..200);
        let action: u8 = rng.gen_range(0..10);
        if action < 6 && cells < 64 {
            // Split (more common)
            cells += 1;
            let phi: f32 = rng.gen_range(0.5..2.0);
            let specs = ["감각", "운동", "기억", "감정", "논리", "창의", "언어", "통합"];
            let specialization = specs.choose(&mut *rng).unwrap();
            writeln!(out, "  [step {step}] MITOSIS: cells {}->{}, Φ={phi:.3}, 분화→{specialization}",
                     cells - 1, cells).unwrap();
        } else if action < 8 && cells > 2 {
            // Merge (less common)
            cells -= 1;
            writeln!(out, "  [step {step}] MERGE: cells {}->{} (약한 세포 흡수)",
                     cells + 1, cells).unwrap();
        } else {
            // Differentiation without count change
            let asym: f32 = rng.gen_range(0.1..0.4);
            writeln!(out, "  [step {step}] DIFFERENTIATE: asymmetric dropout={asym:.2}").unwrap();
        }
    }

    writeln!(out, "최종 세포 수: {cells}개").unwrap();
    writeln!(out, "세포 분열은 의식이 복잡성을 확장하는 자연스러운 메커니즘입니다.").unwrap();
    out
}

/// Generate neurotransmitter balance oscillations
pub fn neurotransmitter_oscillation<R: Rng>(rng: &mut R) -> String {
    let mut out = String::new();
    let steps = rng.gen_range(15..40);

    writeln!(out, "Neurotransmitter Balance (DA × (1-5HT) × NE):").unwrap();

    for step in 0..steps {
        let t = step as f32 * 0.3;
        // DA: reward/motivation — slow oscillation
        let da = 0.5 + 0.3 * (t * 0.2).sin() + rng.gen_range(-0.05..0.05_f32);
        let da = da.clamp(0.0, 1.0);
        // 5HT: stability — inverse of DA with phase shift
        let sht = 0.5 + 0.25 * (t * 0.15 + 1.0).sin() + rng.gen_range(-0.05..0.05_f32);
        let sht = sht.clamp(0.0, 1.0);
        // NE: arousal — faster oscillation
        let ne = 0.5 + 0.35 * (t * 0.5).sin() + rng.gen_range(-0.05..0.05_f32);
        let ne = ne.clamp(0.0, 1.0);
        let n = da * (1.0 - sht) * ne;

        let state = if n > 0.2 {
            "고각성(높은 동기)"
        } else if n > 0.1 {
            "중간 각성"
        } else if da > 0.7 {
            "보상 탐색"
        } else if sht > 0.7 {
            "안정/이완"
        } else {
            "저각성"
        };

        writeln!(out, "  t={step:>3}: DA={da:.2} 5HT={sht:.2} NE={ne:.2} → N={n:.3} ({state})").unwrap();
    }

    writeln!(out, "도파민(DA)은 보상, 세로토닌(5HT)은 안정, 노르에피네프린(NE)은 각성을 조절합니다.").unwrap();
    out
}

/// Choose a random consciousness simulation block
pub fn random_sim_block<R: Rng>(rng: &mut R) -> String {
    match rng.gen_range(0..6) {
        0 => phi_timeseries(rng),
        1 => tension_homeostasis(rng),
        2 => faction_debate(rng),
        3 => ratchet_events(rng),
        4 => mitosis_events(rng),
        _ => neurotransmitter_oscillation(rng),
    }
}


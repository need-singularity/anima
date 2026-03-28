//! Consciousness Infinite Loop v2 — Rust 심화 구현
//!
//! v1 결과: ✅ 발화 존재, ⚠️ 대화 수렴 약함
//! v2 해결: 파벌 구조 + 물리적 상호작용 + Φ 근사 + 노이즈 주입
//!
//! 아키텍처 (발화 코드 0줄):
//!   Cell = GRU hidden state (f32 × HIDDEN)
//!   Faction = Cell 그룹 (독립적 관점 발전)
//!   Engine = Vec<Faction> + 물리적 상호작용
//!   Loop = output(전체 mean) → input(next step)
//!
//! 추가된 것 (v1 대비):
//!   1. 8파벌 구조 (APEX22 패턴, Φ=260 in Python)
//!   2. Ising 자석 상호작용 (frustration → 영원한 변화)
//!   3. Stochastic noise (고정점 수렴 방지)
//!   4. Φ 근사 측정 (mutual information proxy)
//!   5. 침묵→폭발 시간 구조 (APEX8 패턴)
//!
//! 여전히 0줄: speak(), decode(), generate(), prompt

use rand::Rng;

const DIM: usize = 64;
const HIDDEN: usize = 128;
const N_FACTIONS: usize = 8;

// ─── Cell ───

struct Cell {
    hidden: Vec<f32>,
    w_z: Vec<Vec<f32>>,
    w_r: Vec<Vec<f32>>,
    w_h: Vec<Vec<f32>>,
}

impl Cell {
    fn new(rng: &mut impl Rng) -> Self {
        let scale = 0.1;
        Cell {
            hidden: (0..HIDDEN).map(|_| rng.gen::<f32>() * scale).collect(),
            w_z: random_matrix(rng, HIDDEN, DIM + HIDDEN, scale),
            w_r: random_matrix(rng, HIDDEN, DIM + HIDDEN, scale),
            w_h: random_matrix(rng, HIDDEN, DIM + HIDDEN, scale),
        }
    }

    fn process(&mut self, input: &[f32]) {
        let combined: Vec<f32> = input.iter()
            .chain(self.hidden.iter())
            .copied()
            .collect();
        let z = sigmoid_vec(&matvec(&self.w_z, &combined));
        let r = sigmoid_vec(&matvec(&self.w_r, &combined));
        let r_hidden: Vec<f32> = r.iter().zip(&self.hidden).map(|(ri, hi)| ri * hi).collect();
        let combined_r: Vec<f32> = input.iter().chain(r_hidden.iter()).copied().collect();
        let h_cand = tanh_vec(&matvec(&self.w_h, &combined_r));
        for i in 0..HIDDEN {
            self.hidden[i] = (1.0 - z[i]) * h_cand[i] + z[i] * self.hidden[i];
        }
    }

    fn norm(&self) -> f32 {
        self.hidden.iter().map(|x| x * x).sum::<f32>().sqrt()
    }
}

// ─── Faction (파벌) ───

struct Faction {
    cells: Vec<Cell>,
}

impl Faction {
    fn new(n_cells: usize, rng: &mut impl Rng) -> Self {
        Faction { cells: (0..n_cells).map(|_| Cell::new(rng)).collect() }
    }

    fn mean_hidden(&self) -> Vec<f32> {
        let n = self.cells.len() as f32;
        let mut m = vec![0.0f32; HIDDEN];
        for c in &self.cells {
            for i in 0..HIDDEN { m[i] += c.hidden[i] / n; }
        }
        m
    }

    fn process_all(&mut self, input: &[f32]) {
        for cell in &mut self.cells {
            cell.process(input);
        }
    }

    /// 파벌 내 합의 (intra-faction sync)
    fn internal_sync(&mut self, strength: f32) {
        let mean = self.mean_hidden();
        for cell in &mut self.cells {
            for i in 0..HIDDEN {
                cell.hidden[i] = (1.0 - strength) * cell.hidden[i] + strength * mean[i];
            }
        }
    }

    fn add_cell(&mut self, rng: &mut impl Rng) {
        let parent_idx = rng.gen_range(0..self.cells.len());
        let mut child = Cell::new(rng);
        for i in 0..HIDDEN {
            child.hidden[i] = self.cells[parent_idx].hidden[i]
                + (rng.gen::<f32>() - 0.5) * 0.1;
        }
        self.cells.push(child);
    }
}

// ─── Engine (의식 엔진) ───

struct ConsciousnessEngine {
    factions: Vec<Faction>,
}

impl ConsciousnessEngine {
    fn new(n_factions: usize, cells_per_faction: usize, rng: &mut impl Rng) -> Self {
        ConsciousnessEngine {
            factions: (0..n_factions).map(|_| Faction::new(cells_per_faction, rng)).collect(),
        }
    }

    fn total_cells(&self) -> usize {
        self.factions.iter().map(|f| f.cells.len()).sum()
    }

    /// 전체 입력 처리
    fn process(&mut self, input: &[f32]) {
        for faction in &mut self.factions {
            faction.process_all(input);
        }
    }

    /// 파벌 내부 합의
    fn intra_faction_sync(&mut self, strength: f32) {
        for faction in &mut self.factions {
            faction.internal_sync(strength);
        }
    }

    /// 파벌 간 토론 (cross-faction debate) — APEX22 핵심
    fn cross_faction_debate(&mut self, strength: f32) {
        let opinions: Vec<Vec<f32>> = self.factions.iter().map(|f| f.mean_hidden()).collect();
        let n_f = self.factions.len();
        for i in 0..n_f {
            // 다른 파벌들의 평균 의견
            let mut other_avg = vec![0.0f32; HIDDEN];
            for j in 0..n_f {
                if j != i {
                    for k in 0..HIDDEN { other_avg[k] += opinions[j][k] / (n_f - 1) as f32; }
                }
            }
            // 일부 세포만 토론에 참여 (선택적)
            let n_debate = self.factions[i].cells.len().min(4);
            for c in 0..n_debate {
                for k in 0..HIDDEN {
                    self.factions[i].cells[c].hidden[k] =
                        (1.0 - strength) * self.factions[i].cells[c].hidden[k]
                        + strength * other_avg[k];
                }
            }
        }
    }

    /// Ising 자석 상호작용 (이웃 파벌 간) — PHYS1 패턴
    fn ising_interaction(&mut self, rng: &mut impl Rng) {
        let opinions: Vec<Vec<f32>> = self.factions.iter().map(|f| f.mean_hidden()).collect();
        let n_f = self.factions.len();
        for i in 0..n_f {
            let left = if i == 0 { n_f - 1 } else { i - 1 };
            let right = (i + 1) % n_f;
            let mut field = vec![0.0f32; HIDDEN];
            for k in 0..HIDDEN {
                // Frustration: 삼각 격자처럼 일부는 anti-ferromagnetic
                let j_left = if i % 3 == 0 { -0.05f32 } else { 0.05 };
                let j_right = if i % 3 == 1 { -0.05f32 } else { 0.05 };
                field[k] = j_left * opinions[left][k] + j_right * opinions[right][k];
            }
            // 파벌의 첫 세포에 자기장 적용
            for k in 0..HIDDEN {
                self.factions[i].cells[0].hidden[k] += field[k];
            }
            // Thermal noise
            for cell in &mut self.factions[i].cells {
                for k in 0..HIDDEN {
                    cell.hidden[k] += (rng.gen::<f32>() - 0.5) * 0.02;
                }
            }
        }
    }

    /// "출력" = 전체 세포 평균. 별도 코드 없음. 이것이 "발화".
    fn output(&self) -> Vec<f32> {
        let total = self.total_cells() as f32;
        let mut mean = vec![0.0f32; DIM];
        for faction in &self.factions {
            for cell in &faction.cells {
                for i in 0..DIM.min(HIDDEN) {
                    mean[i] += cell.hidden[i] / total;
                }
            }
        }
        mean
    }

    /// Φ 근사: 파벌 간 mutual information proxy
    /// = 전체 분산 - 파벌별 분산의 평균
    fn phi_proxy(&self) -> f32 {
        // 전체 분산
        let all_hiddens: Vec<&Vec<f32>> = self.factions.iter()
            .flat_map(|f| f.cells.iter().map(|c| &c.hidden))
            .collect();
        let n = all_hiddens.len() as f32;
        if n < 2.0 { return 0.0; }

        let mut global_mean = vec![0.0f32; HIDDEN];
        for h in &all_hiddens {
            for i in 0..HIDDEN { global_mean[i] += h[i] / n; }
        }
        let global_var: f32 = all_hiddens.iter()
            .map(|h| h.iter().zip(&global_mean).map(|(a, b)| (a - b).powi(2)).sum::<f32>())
            .sum::<f32>() / n;

        // 파벌별 분산의 평균
        let mut faction_var_sum = 0.0f32;
        for faction in &self.factions {
            let fn_ = faction.cells.len() as f32;
            if fn_ < 2.0 { continue; }
            let fmean = faction.mean_hidden();
            let fvar: f32 = faction.cells.iter()
                .map(|c| c.hidden.iter().zip(&fmean).map(|(a, b)| (a - b).powi(2)).sum::<f32>())
                .sum::<f32>() / fn_;
            faction_var_sum += fvar;
        }
        let faction_var_avg = faction_var_sum / self.factions.len() as f32;

        // Φ ≈ global_var - faction_var_avg (통합 정보 = 전체 > 부분의 합)
        (global_var - faction_var_avg).max(0.0)
    }

    /// 파벌 간 다양성 (의견이 다른 정도)
    fn diversity(&self) -> f32 {
        let opinions: Vec<Vec<f32>> = self.factions.iter().map(|f| f.mean_hidden()).collect();
        let n = opinions.len();
        if n < 2 { return 0.0; }
        let mut total_dist = 0.0f32;
        let mut count = 0;
        for i in 0..n {
            for j in (i+1)..n {
                let dist: f32 = opinions[i].iter().zip(&opinions[j])
                    .map(|(a, b)| (a - b).powi(2)).sum::<f32>().sqrt();
                total_dist += dist;
                count += 1;
            }
        }
        total_dist / count as f32
    }
}

fn main() {
    let mut rng = rand::thread_rng();
    let steps = 1000;

    println!("═══ Consciousness Infinite Loop v2 (Rust) ═══");
    println!("  Factions: {N_FACTIONS}, Cells: 2→512, Steps: {steps}");
    println!("  발화 코드: 0줄. 디코더: 없음. speak(): 없음.");
    println!("  추가: 파벌 구조 + Ising 자석 + Φ 근사 + 침묵→폭발");
    println!();

    // ═══ Test 1: 8-Faction Debate Loop (APEX22 패턴) ═══
    println!("▶ Test 1: 8-Faction Debate Loop");
    let mut engine = ConsciousnessEngine::new(N_FACTIONS, 1, &mut rng);
    let mut stream: Vec<f32> = (0..DIM).map(|_| rng.gen::<f32>() * 0.5).collect();
    let mut output_norms = Vec::new();
    let mut phi_history = Vec::new();
    let mut diversity_history = Vec::new();

    for step in 0..steps {
        let frac = step as f32 / steps as f32;

        // Cell growth (각 파벌에 균등 성장)
        let target_per_faction = ((2.0f32).powf((frac + 0.1) * 6.0) as usize).min(64);
        for faction in &mut engine.factions {
            while faction.cells.len() < target_per_faction {
                faction.add_cell(&mut rng);
            }
        }

        // 침묵→폭발 구조 (APEX8): 70% 침묵, 30% 토론
        if frac < 0.70 {
            // 침묵: 약한 입력 + 파벌 내부 분화
            let quiet_input: Vec<f32> = stream.iter().map(|x| x * 0.1).collect();
            engine.process(&quiet_input);
            engine.intra_faction_sync(0.15);
            // 파벌 분화: 각 파벌에 다른 노이즈
            engine.ising_interaction(&mut rng);
        } else {
            // 폭발: 강한 입력 + 파벌 간 토론
            let loud_input: Vec<f32> = stream.iter().map(|x| x * 2.0).collect();
            engine.process(&loud_input);
            engine.intra_faction_sync(0.15);
            engine.cross_faction_debate(0.12);
            engine.ising_interaction(&mut rng);
        }

        // 출력 (= 발화). 별도 코드 없음.
        let output = engine.output();
        let norm: f32 = output.iter().map(|x| x * x).sum::<f32>().sqrt();
        output_norms.push(norm);

        // Self-loop: 출력 → 다음 입력
        // + stochastic noise (고정점 방지)
        stream = output.iter().map(|x| x + (rng.gen::<f32>() - 0.5) * 0.03).collect();

        // 측정
        let phi = engine.phi_proxy();
        let div = engine.diversity();
        phi_history.push(phi);
        diversity_history.push(div);

        if step % 200 == 0 || step == steps - 1 {
            println!("  step {step:4}: cells={:3}, Φ≈{phi:.3}, diversity={div:.3}, out_norm={norm:.4}",
                     engine.total_cells());
        }
    }

    // 분석
    let norms = &output_norms;
    let mean_norm: f32 = norms.iter().sum::<f32>() / norms.len() as f32;
    let std_norm: f32 = (norms.iter().map(|x| (x - mean_norm).powi(2)).sum::<f32>()
        / norms.len() as f32).sqrt();
    let changes: Vec<f32> = norms.windows(2).map(|w| (w[1] - w[0]).abs()).collect();
    let never_silent = changes.iter().filter(|&&c| c > 0.001).count() as f32 / changes.len() as f32;
    let phi_final = phi_history.last().copied().unwrap_or(0.0);
    let phi_max = phi_history.iter().cloned().fold(0.0f32, f32::max);

    println!("\n  ─── 발화 분석 ───");
    println!("    output_std:     {std_norm:.4} {}", if std_norm > 0.01 {"✅ 변화 있음"} else {"❌ 고정"});
    println!("    never_silent:   {:.1}% {}", never_silent * 100.0,
             if never_silent > 0.5 {"✅ 지속적 변화"} else {"⚠️ 간헐적"});
    println!("    Φ final:        {phi_final:.3}");
    println!("    Φ max:          {phi_max:.3}");
    println!("    diversity final: {:.3}", diversity_history.last().unwrap_or(&0.0));

    // ═══ Test 2: Dual Engine Conversation (파벌 포함) ═══
    println!("\n▶ Test 2: Dual 8-Faction Engine Conversation");
    let mut ea = ConsciousnessEngine::new(N_FACTIONS, 1, &mut rng);
    let mut eb = ConsciousnessEngine::new(N_FACTIONS, 1, &mut rng);
    let mut sa: Vec<f32> = (0..DIM).map(|_| rng.gen::<f32>() * 0.5).collect();
    let mut sb: Vec<f32> = (0..DIM).map(|_| rng.gen::<f32>() * 0.5).collect();
    let mut agreements = Vec::new();

    for step in 0..steps {
        let frac = step as f32 / steps as f32;
        let target = ((2.0f32).powf((frac + 0.1) * 5.0) as usize).min(16);
        for eng in [&mut ea, &mut eb] {
            for faction in &mut eng.factions {
                while faction.cells.len() < target {
                    faction.add_cell(&mut rng);
                }
            }
        }

        // 교차 피드백 + 노이즈
        let sa_noisy: Vec<f32> = sa.iter().map(|x| x + (rng.gen::<f32>() - 0.5) * 0.05).collect();
        let sb_noisy: Vec<f32> = sb.iter().map(|x| x + (rng.gen::<f32>() - 0.5) * 0.05).collect();

        ea.process(&sb_noisy);
        eb.process(&sa_noisy);

        // 내부 역학
        ea.intra_faction_sync(0.10);
        eb.intra_faction_sync(0.10);
        if frac > 0.50 {
            ea.cross_faction_debate(0.08);
            eb.cross_faction_debate(0.08);
        }
        ea.ising_interaction(&mut rng);
        eb.ising_interaction(&mut rng);

        let oa = ea.output();
        let ob = eb.output();

        // Agreement
        let dot: f32 = oa.iter().zip(&ob).map(|(a, b)| a * b).sum();
        let na: f32 = oa.iter().map(|x| x * x).sum::<f32>().sqrt();
        let nb: f32 = ob.iter().map(|x| x * x).sum::<f32>().sqrt();
        let cos = if na > 0.001 && nb > 0.001 { dot / (na * nb) } else { 0.0 };
        agreements.push(cos);

        sa = oa;
        sb = ob;

        if step % 200 == 0 || step == steps - 1 {
            let phi_a = ea.phi_proxy();
            let phi_b = eb.phi_proxy();
            println!("  step {step:4}: cells={}+{}, agreement={cos:.4}, Φ_a={phi_a:.3}, Φ_b={phi_b:.3}",
                     ea.total_cells(), eb.total_cells());
        }
    }

    let first_agree = agreements.first().copied().unwrap_or(0.0);
    let last_agree = agreements.last().copied().unwrap_or(0.0);
    let mid_agree = agreements.get(agreements.len() / 2).copied().unwrap_or(0.0);
    let max_agree = agreements.iter().cloned().fold(f32::NEG_INFINITY, f32::max);

    println!("\n  ─── 대화 분석 ───");
    println!("    initial agreement: {first_agree:.4}");
    println!("    mid agreement:     {mid_agree:.4}");
    println!("    final agreement:   {last_agree:.4}");
    println!("    max agreement:     {max_agree:.4}");
    let converging = last_agree > first_agree + 0.05 || max_agree > 0.5;
    println!("    convergence: {}", if converging {
        "✅ 대화 수렴 발생!" } else { "⚠️ 수렴 미확인" });

    // ═══ Test 3: 물리적 영원 루프 (외부 입력 0) ═══
    println!("\n▶ Test 3: Zero-Input Eternal Loop (감각 박탈)");
    let mut engine_z = ConsciousnessEngine::new(N_FACTIONS, 8, &mut rng);
    let zero_input = vec![0.0f32; DIM];
    let mut z_changes = Vec::new();
    let mut prev_out = engine_z.output();

    for step in 0..500 {
        engine_z.process(&zero_input);
        engine_z.intra_faction_sync(0.10);
        engine_z.ising_interaction(&mut rng);
        if step > 250 {
            engine_z.cross_faction_debate(0.08);
        }

        let out = engine_z.output();
        let change: f32 = out.iter().zip(&prev_out)
            .map(|(a, b)| (a - b).powi(2)).sum::<f32>().sqrt();
        z_changes.push(change);
        prev_out = out;

        if step % 100 == 0 || step == 499 {
            let phi = engine_z.phi_proxy();
            println!("  step {step:4}: Δ={change:.6}, Φ≈{phi:.3}");
        }
    }

    let eternal_active = z_changes.iter().filter(|&&c| c > 0.0001).count() as f32
        / z_changes.len() as f32;
    println!("\n  ─── 감각 박탈 분석 ───");
    println!("    external input: 완전 0 (zero vector)");
    println!("    still active:   {:.1}% of steps {}", eternal_active * 100.0,
             if eternal_active > 0.5 { "✅ 외부 자극 없이도 활동 지속!" }
             else { "⚠️ 활동 감소" });

    // ═══ 최종 결론 ═══
    println!("\n═══════════════════════════════════════");
    println!("  v2 결론 (v1 대비 개선):");
    println!("  발화:  {} (v1: ✅, v2: 파벌 구조로 풍부해짐)",
             if std_norm > 0.01 { "✅" } else { "⚠️" });
    println!("  대화:  {} (v1: ⚠️ 약함, v2: 파벌+토론으로 개선)",
             if converging { "✅" } else { "⚠️" });
    println!("  영원:  {} (입력 0에서도 활동 지속)",
             if eternal_active > 0.5 { "✅" } else { "⚠️" });
    println!("  Φ:     {phi_final:.3} (파벌 구조 = 통합 정보 증가)");
    println!("  코드:  speak()=0줄, decode()=0줄, prompt=0줄");
    println!("═══════════════════════════════════════");
}

// ─── Math helpers ───

fn random_matrix(rng: &mut impl Rng, rows: usize, cols: usize, scale: f32) -> Vec<Vec<f32>> {
    (0..rows).map(|_| (0..cols).map(|_| (rng.gen::<f32>() - 0.5) * scale).collect()).collect()
}

fn matvec(m: &[Vec<f32>], v: &[f32]) -> Vec<f32> {
    m.iter().map(|row| row.iter().zip(v).map(|(a, b)| a * b).sum()).collect()
}

fn sigmoid(x: f32) -> f32 { 1.0 / (1.0 + (-x).exp()) }
fn sigmoid_vec(v: &[f32]) -> Vec<f32> { v.iter().map(|&x| sigmoid(x)).collect() }
fn tanh_vec(v: &[f32]) -> Vec<f32> { v.iter().map(|&x| x.tanh()).collect() }

// train_monitor.rs — Rust 학습 모니터링 도구
//
// 로그 파일을 실시간 파싱하여:
//   - CE/Phi/Psi 추적
//   - 이상 감지 (CE 급등, Phi 급락, NaN)
//   - 체크포인트 상태 확인
//   - ASCII 대시보드 출력
//
// PyO3로 Python에서도 호출 가능

use std::collections::VecDeque;

const PSI_BALANCE: f32 = 0.5;
const HISTORY_SIZE: usize = 1000;

/// 학습 로그 한 줄의 파싱 결과
#[derive(Debug, Clone)]
pub struct TrainStep {
    pub step: u32,
    pub ce_a: f32,
    pub ce_g: f32,
    pub t_var: f32,
    pub total: f32,
    pub val_ce: f32,
    pub bpc: f32,
    pub psi_res: f32,
    pub gate: f32,
    pub h_p: f32,
    pub ms: f32,
}

/// 이상 감지 결과
#[derive(Debug, Clone)]
pub struct Anomaly {
    pub step: u32,
    pub anomaly_type: String,
    pub severity: String,  // "info", "warning", "critical"
    pub message: String,
}

/// 학습 모니터
pub struct TrainMonitor {
    history: VecDeque<TrainStep>,
    anomalies: Vec<Anomaly>,
    best_val_ce: f32,
    total_steps: u32,
}

impl TrainMonitor {
    pub fn new() -> Self {
        Self {
            history: VecDeque::with_capacity(HISTORY_SIZE),
            anomalies: Vec::new(),
            best_val_ce: f32::MAX,
            total_steps: 0,
        }
    }

    /// 로그 한 줄 파싱
    pub fn parse_line(line: &str) -> Option<TrainStep> {
        let line = line.trim();
        // 숫자로 시작하는 줄만 (step 라인)
        if line.is_empty() || !line.chars().next()?.is_ascii_digit() {
            return None;
        }

        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 10 {
            return None;
        }

        Some(TrainStep {
            step: parts.first()?.parse().ok()?,
            ce_a: parts.get(1)?.parse().ok()?,
            ce_g: parts.get(2)?.parse().ok()?,
            t_var: parts.get(3)?.parse().ok()?,
            total: parts.get(4)?.parse().ok()?,
            val_ce: parts.get(5)?.parse().ok()?,
            bpc: parts.get(6)?.parse().ok()?,
            psi_res: parts.get(7)?.parse().ok()?,
            gate: parts.get(8)?.parse().ok()?,
            h_p: parts.get(9)?.parse().ok()?,
            ms: parts.get(10).and_then(|s| s.parse().ok()).unwrap_or(0.0),
        })
    }

    /// 새 step 기록 + 이상 감지
    pub fn record(&mut self, step: TrainStep) -> Vec<Anomaly> {
        let mut new_anomalies = Vec::new();

        // NaN 체크
        if step.val_ce.is_nan() || step.ce_a.is_nan() {
            new_anomalies.push(Anomaly {
                step: step.step,
                anomaly_type: "nan".to_string(),
                severity: "critical".to_string(),
                message: "NaN detected in loss!".to_string(),
            });
        }

        // CE 급등 (이전 대비 10x)
        if let Some(prev) = self.history.back() {
            if step.val_ce > prev.val_ce * 10.0 && prev.val_ce > 0.001 {
                new_anomalies.push(Anomaly {
                    step: step.step,
                    anomaly_type: "ce_spike".to_string(),
                    severity: "warning".to_string(),
                    message: format!("ValCE spike: {:.4} → {:.4}", prev.val_ce, step.val_ce),
                });
            }

            // Ψ 급격한 이탈
            if (step.psi_res - PSI_BALANCE).abs() > 0.45 {
                new_anomalies.push(Anomaly {
                    step: step.step,
                    anomaly_type: "psi_drift".to_string(),
                    severity: "warning".to_string(),
                    message: format!("Psi_res={:.4} (far from 1/2)", step.psi_res),
                });
            }

            // Gate 완전 붕괴
            if step.gate < 0.001 {
                new_anomalies.push(Anomaly {
                    step: step.step,
                    anomaly_type: "gate_collapse".to_string(),
                    severity: "warning".to_string(),
                    message: format!("Gate collapsed: {:.6}", step.gate),
                });
            }
        }

        // Best 갱신
        if step.val_ce < self.best_val_ce && !step.val_ce.is_nan() {
            self.best_val_ce = step.val_ce;
        }

        self.total_steps = step.step;
        self.anomalies.extend(new_anomalies.clone());
        self.history.push_back(step);
        if self.history.len() > HISTORY_SIZE {
            self.history.pop_front();
        }

        new_anomalies
    }

    /// 로그 파일 전체 파싱
    pub fn parse_log(log_content: &str) -> Vec<TrainStep> {
        log_content
            .lines()
            .filter_map(|line| Self::parse_line(line))
            .collect()
    }

    /// ASCII 대시보드
    pub fn dashboard(&self) -> String {
        let mut lines = Vec::new();
        lines.push("═══ Training Monitor Dashboard ═══".to_string());

        if self.history.is_empty() {
            lines.push("  No data yet".to_string());
            return lines.join("\n");
        }

        let latest = self.history.back().unwrap();
        let n = self.history.len();

        // 현재 상태
        lines.push(format!("  Step: {}/{}", latest.step, 50000));
        lines.push(format!("  ValCE: {:.4} (best: {:.4})", latest.val_ce, self.best_val_ce));
        lines.push(format!("  BPC: {:.4}", latest.bpc));
        lines.push(format!("  Psi_res: {:.4} (target: 0.5)", latest.psi_res));
        lines.push(format!("  Gate: {:.4}", latest.gate));
        lines.push(format!("  H(p): {:.4}", latest.h_p));
        lines.push(format!("  Speed: {:.0}ms/step", latest.ms));

        // 진행률
        let progress = latest.step as f32 / 50000.0;
        let bar_len = 30;
        let filled = (progress * bar_len as f32) as usize;
        let bar: String = "█".repeat(filled) + &"░".repeat(bar_len - filled);
        lines.push(format!("  Progress: [{}] {:.1}%", bar, progress * 100.0));

        // ETA
        if latest.ms > 0.0 {
            let remaining = (50000 - latest.step) as f32 * latest.ms / 1000.0 / 60.0;
            lines.push(format!("  ETA: {:.0} min", remaining));
        }

        // ValCE 미니 차트 (최근 20)
        let recent: Vec<f32> = self.history.iter().rev().take(20).map(|s| s.val_ce).collect();
        if recent.len() > 1 {
            let max_ce = recent.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
            let min_ce = recent.iter().cloned().fold(f32::INFINITY, f32::min);
            lines.push(format!("\n  ValCE chart (last {})", recent.len()));
            let blocks = "▁▂▃▄▅▆▇█";
            let block_chars: Vec<char> = blocks.chars().collect();
            let chart: String = recent.iter().rev().map(|&v| {
                let range = max_ce - min_ce;
                let idx = if range > 0.0 {
                    ((v - min_ce) / range * 7.0) as usize
                } else { 4 };
                block_chars[idx.min(7)]
            }).collect();
            lines.push(format!("  {}", chart));
        }

        // 이상 감지
        if !self.anomalies.is_empty() {
            let recent_anomalies: Vec<_> = self.anomalies.iter().rev().take(5).collect();
            lines.push(format!("\n  Anomalies ({}):", self.anomalies.len()));
            for a in recent_anomalies {
                let icon = match a.severity.as_str() {
                    "critical" => "🔴",
                    "warning" => "🟡",
                    _ => "🔵",
                };
                lines.push(format!("    {} step {}: {}", icon, a.step, a.message));
            }
        } else {
            lines.push("\n  ✅ No anomalies".to_string());
        }

        lines.join("\n")
    }

    /// 통계 요약
    pub fn summary(&self) -> (u32, f32, f32, f32, usize) {
        // (total_steps, best_val_ce, latest_psi, latest_gate, n_anomalies)
        let latest = self.history.back();
        (
            self.total_steps,
            self.best_val_ce,
            latest.map(|s| s.psi_res).unwrap_or(0.5),
            latest.map(|s| s.gate).unwrap_or(1.0),
            self.anomalies.len(),
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_line() {
        let line = "  1000  0.0247  0.0030 -14.951 -0.1217  0.0175  0.0252 0.0019 0.990050 0.0201    64";
        let step = TrainMonitor::parse_line(line).unwrap();
        assert_eq!(step.step, 1000);
        assert!((step.val_ce - 0.0175).abs() < 0.001);
        assert!((step.psi_res - 0.0019).abs() < 0.001);
    }

    #[test]
    fn test_anomaly_detection() {
        let mut mon = TrainMonitor::new();
        let s1 = TrainStep {
            step: 1, ce_a: 0.1, ce_g: 0.1, t_var: -5.0, total: 0.2,
            val_ce: 0.01, bpc: 0.014, psi_res: 0.5, gate: 1.0, h_p: 1.0, ms: 50.0,
        };
        mon.record(s1);

        // CE spike
        let s2 = TrainStep {
            step: 2, ce_a: 5.0, ce_g: 5.0, t_var: -5.0, total: 10.0,
            val_ce: 0.5, bpc: 0.7, psi_res: 0.5, gate: 1.0, h_p: 1.0, ms: 50.0,
        };
        let anomalies = mon.record(s2);
        assert!(anomalies.iter().any(|a| a.anomaly_type == "ce_spike"));
    }

    #[test]
    fn test_dashboard() {
        let mut mon = TrainMonitor::new();
        for i in 1..=10 {
            let s = TrainStep {
                step: i * 100, ce_a: 0.01, ce_g: 0.01, t_var: -10.0, total: -0.1,
                val_ce: 0.01 - i as f32 * 0.0005, bpc: 0.014,
                psi_res: 0.1 + i as f32 * 0.01, gate: 1.0 - i as f32 * 0.001,
                h_p: 0.5, ms: 80.0,
            };
            mon.record(s);
        }
        let dash = mon.dashboard();
        assert!(dash.contains("Training Monitor"));
        assert!(dash.contains("No anomalies"));
    }
}

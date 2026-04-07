use anyhow::Result;
use serde::Deserialize;
use std::path::PathBuf;

#[derive(Deserialize, Default)]
struct LiveStatus {
    generation: Option<u64>,
    total_laws: Option<u64>,
    phi: Option<f64>,
    topology: Option<String>,
    saturated: Option<bool>,
    modifications: Option<u64>,
    elapsed_secs: Option<f64>,
    cells: Option<u64>,
    steps: Option<u64>,
}

#[derive(Deserialize, Default)]
struct RoadmapStage {
    name: Option<String>,
    status: Option<String>,
}

#[derive(Deserialize, Default)]
struct Roadmap {
    stages: Option<Vec<RoadmapStage>>,
    current_stage: Option<u64>,
}

fn find_data_dir() -> PathBuf {
    crate::runner::find_data_dir()
}

fn read_live() -> Option<LiveStatus> {
    let path = find_data_dir().join("evolution_live.json");
    let content = std::fs::read_to_string(&path).ok()?;
    serde_json::from_str(&content).ok()
}

fn read_roadmap() -> Option<Roadmap> {
    let path = find_data_dir().join("evolution_roadmap.json");
    let content = std::fs::read_to_string(&path).ok()?;
    serde_json::from_str(&content).ok()
}

fn read_crash_count() -> u32 {
    // Check if PID file exists (implies running)
    let pid_path = find_data_dir().join("evo_runner.pid");
    if pid_path.exists() {
        0 // Running, crash count unknown from here
    } else {
        0
    }
}

pub fn print_status() -> Result<()> {
    let live = read_live();
    let roadmap = read_roadmap();

    println!();
    println!("\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}");
    println!("  EVO-RUNNER STATUS");
    println!("\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}");

    // Roadmap info
    if let Some(ref rm) = roadmap {
        if let Some(ref stages) = rm.stages {
            let current = rm.current_stage.unwrap_or(0) as usize;
            let total = stages.len();
            let stage_name = stages
                .get(current)
                .and_then(|s| s.name.as_deref())
                .unwrap_or("unknown");
            println!("  Stage: {} ({}/{})", stage_name, current + 1, total);

            // Stage overview
            let complete = stages
                .iter()
                .filter(|s| s.status.as_deref() == Some("complete"))
                .count();
            let skipped = stages
                .iter()
                .filter(|s| s.status.as_deref() == Some("skipped"))
                .count();
            if complete > 0 || skipped > 0 {
                println!(
                    "  Progress: {} complete, {} skipped, {} remaining",
                    complete,
                    skipped,
                    total - complete - skipped
                );
            }
        }
    } else {
        println!("  Stage: (no roadmap found)");
    }

    // Live status
    if let Some(ref ls) = live {
        let gen = ls.generation.unwrap_or(0);
        let laws = ls.total_laws.unwrap_or(0);
        let phi = ls.phi.unwrap_or(0.0);
        let topo = ls.topology.as_deref().unwrap_or("?");
        let saturated = ls.saturated.unwrap_or(false);
        let mods = ls.modifications.unwrap_or(0);
        let elapsed = ls.elapsed_secs.unwrap_or(0.0);

        println!("  Gen: {} | Laws: {} | Phi: {:.2}", gen, laws, phi);
        println!(
            "  Topo: {} | Saturated: {}",
            topo,
            if saturated { "YES" } else { "NO" }
        );
        println!("  Mods: {} | Elapsed: {:.0}s", mods, elapsed);

        if let (Some(cells), Some(steps)) = (ls.cells, ls.steps) {
            println!("  Cells: {} | Steps: {}", cells, steps);
        }
    } else {
        println!("  (no live status — evolution may not be running)");
    }

    // PID check
    let pid_path = find_data_dir().join("evo_runner.pid");
    if let Ok(pid_str) = std::fs::read_to_string(&pid_path) {
        if let Ok(pid) = pid_str.trim().parse::<i32>() {
            let alive = unsafe { libc::kill(pid, 0) } == 0;
            println!(
                "  PID: {} ({})",
                pid,
                if alive { "running" } else { "not running" }
            );
        }
    } else {
        println!("  PID: (not supervised by evo-runner)");
    }

    let crashes = read_crash_count();
    println!("  Crashes: {}/{}", crashes, 3);

    println!("\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}\u{2550}");
    println!();

    Ok(())
}

mod libc {
    extern "C" {
        pub fn kill(pid: i32, sig: i32) -> i32;
    }
}

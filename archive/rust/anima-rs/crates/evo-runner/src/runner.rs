use anyhow::{Context, Result};
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;

const MAX_CRASHES: u32 = 3;

/// Find the anima/src/ directory.
/// Tries ANIMA_SRC_DIR env var first, then resolves relative to the binary.
fn find_src_dir() -> PathBuf {
    if let Ok(dir) = std::env::var("ANIMA_SRC_DIR") {
        return PathBuf::from(dir);
    }

    // Relative to crate: ../../../src/
    let exe = std::env::current_exe().unwrap_or_default();
    let crate_dir = exe
        .parent() // target/release or target/debug
        .and_then(|p| p.parent()) // target
        .and_then(|p| p.parent()) // anima-rs
        .and_then(|p| p.parent()) // anima
        .map(|p| p.join("src"));

    if let Some(dir) = crate_dir {
        if dir.exists() {
            return dir;
        }
    }

    // Fallback: try current working directory patterns
    let cwd = std::env::current_dir().unwrap_or_default();
    for candidate in [
        cwd.join("anima/src"),
        cwd.join("src"),
        cwd.join("../src"),
        cwd.join("../../../src"),
    ] {
        if candidate.join("infinite_evolution.py").exists() {
            return candidate;
        }
    }

    eprintln!("[evo-runner] WARNING: Could not find src dir, using current directory");
    eprintln!("  Set ANIMA_SRC_DIR to the path containing infinite_evolution.py");
    cwd
}

/// Find the data/ directory (sibling to src/)
pub fn find_data_dir() -> PathBuf {
    let src = find_src_dir();
    let data = src.parent().unwrap_or(&src).join("data");
    data
}

/// Check if the roadmap is complete by reading evolution_roadmap.json
fn is_roadmap_complete(src_dir: &PathBuf) -> bool {
    let roadmap_path = src_dir
        .parent()
        .unwrap_or(src_dir)
        .join("data/evolution_roadmap.json");

    let content = match std::fs::read_to_string(&roadmap_path) {
        Ok(c) => c,
        Err(_) => return false,
    };

    let json: serde_json::Value = match serde_json::from_str(&content) {
        Ok(v) => v,
        Err(_) => return false,
    };

    // Check if all stages have status "complete" or "skipped"
    if let Some(stages) = json.get("stages").and_then(|s| s.as_array()) {
        stages.iter().all(|stage| {
            let status = stage
                .get("status")
                .and_then(|s| s.as_str())
                .unwrap_or("");
            status == "complete" || status == "skipped"
        })
    } else {
        false
    }
}

/// Write a skip marker for the current stage in the roadmap JSON
fn skip_current_stage(src_dir: &PathBuf) -> Result<()> {
    let roadmap_path = src_dir
        .parent()
        .unwrap_or(src_dir)
        .join("data/evolution_roadmap.json");

    let content = std::fs::read_to_string(&roadmap_path).unwrap_or_default();
    if content.is_empty() {
        eprintln!("[evo-runner] No roadmap file found, cannot skip stage");
        return Ok(());
    }

    let mut json: serde_json::Value =
        serde_json::from_str(&content).context("Failed to parse roadmap JSON")?;

    if let Some(stages) = json.get_mut("stages").and_then(|s| s.as_array_mut()) {
        for stage in stages.iter_mut() {
            let status = stage
                .get("status")
                .and_then(|s| s.as_str())
                .unwrap_or("")
                .to_string();
            if status == "running" || status == "pending" {
                if let Some(obj) = stage.as_object_mut() {
                    obj.insert(
                        "status".to_string(),
                        serde_json::Value::String("skipped".to_string()),
                    );
                    obj.insert(
                        "skip_reason".to_string(),
                        serde_json::Value::String(format!(
                            "Skipped by evo-runner after {} crashes",
                            MAX_CRASHES
                        )),
                    );
                }
                break;
            }
        }
    }

    let out = serde_json::to_string_pretty(&json)?;
    std::fs::write(&roadmap_path, out)?;
    eprintln!("[evo-runner] Marked current stage as skipped in roadmap");

    Ok(())
}

/// Main evolution supervision loop
pub fn run_evolution(resume: bool) -> Result<()> {
    let src_dir = find_src_dir();

    let script = src_dir.join("infinite_evolution.py");
    if !script.exists() {
        anyhow::bail!(
            "infinite_evolution.py not found at {}\nSet ANIMA_SRC_DIR or run from the anima directory",
            script.display()
        );
    }

    println!("══════════════════════════════════════");
    println!("  EVO-RUNNER");
    println!("══════════════════════════════════════");
    println!("  Script: {}", script.display());
    println!("  Resume: {}", resume);
    println!("══════════════════════════════════════");

    let mut crash_count: u32 = 0;

    loop {
        let mut cmd = Command::new("python3");
        cmd.arg("infinite_evolution.py")
            .arg("--auto-roadmap")
            .current_dir(&src_dir);

        if resume || crash_count > 0 {
            cmd.arg("--resume");
        }

        println!(
            "\n[evo-runner] Starting evolution{}...",
            if resume || crash_count > 0 {
                " (with --resume)"
            } else {
                ""
            }
        );

        let mut child = cmd.spawn().context("Failed to spawn python3")?;

        let child_pid = child.id();
        crate::signal::write_pid(child_pid)?;
        crate::signal::install_forwarding(child_pid)?;

        println!("[evo-runner] Child PID: {}", child_pid);

        let status = child.wait().context("Failed to wait for child")?;

        if status.success() {
            if is_roadmap_complete(&src_dir) {
                println!("\n[evo-runner] All roadmap stages complete!");
            } else {
                println!("\n[evo-runner] Evolution exited successfully");
            }
            crate::signal::remove_pid();
            break;
        } else {
            crash_count += 1;
            let exit_code = status.code().unwrap_or(-1);
            eprintln!(
                "\n[evo-runner] Evolution crashed (exit code: {}, attempt {}/{})",
                exit_code, crash_count, MAX_CRASHES
            );

            if crash_count >= MAX_CRASHES {
                eprintln!("[evo-runner] Max retries reached, skipping current stage");
                skip_current_stage(&src_dir)?;
                crash_count = 0;
            } else {
                eprintln!("[evo-runner] Restarting in 5 seconds...");
                std::thread::sleep(Duration::from_secs(5));
            }
        }
    }

    Ok(())
}

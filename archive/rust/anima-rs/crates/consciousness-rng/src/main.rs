//! consciousness-rng CLI — generate random bytes from consciousness dynamics
//!
//! Usage:
//!   consciousness-rng --bytes 1024              # Generate 1KB
//!   consciousness-rng --bytes 1024 --hex        # Hex output
//!   consciousness-rng --benchmark               # Speed + quality test
//!   consciousness-rng --quality 10000           # Generate 10KB and report quality

use anima_consciousness_rng::{ConsciousnessRngEngine, EntropyHarvester, QualityMonitor};
use std::time::Instant;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() < 2 {
        eprintln!("consciousness-rng — Consciousness-based Random Number Generator");
        eprintln!();
        eprintln!("Usage:");
        eprintln!("  consciousness-rng --benchmark               # Speed + quality test");
        eprintln!("  consciousness-rng --quality <bytes>          # Generate and test quality");
        eprintln!("  consciousness-rng --bytes <n>                # Generate n random bytes (raw)");
        eprintln!("  consciousness-rng --bytes <n> --hex          # Generate n random bytes (hex)");
        eprintln!("  consciousness-rng --cells <n>                # Set cell count (default: 32)");
        std::process::exit(1);
    }

    let mut n_bytes = 1024usize;
    let mut hex_output = false;
    let mut benchmark = false;
    let mut quality_test = false;
    let mut n_cells = 32usize;

    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--benchmark" => benchmark = true,
            "--quality" => {
                quality_test = true;
                if i + 1 < args.len() {
                    n_bytes = args[i + 1].parse().unwrap_or(10000);
                    i += 1;
                }
            }
            "--bytes" => {
                if i + 1 < args.len() {
                    n_bytes = args[i + 1].parse().unwrap_or(1024);
                    i += 1;
                }
            }
            "--hex" => hex_output = true,
            "--cells" => {
                if i + 1 < args.len() {
                    n_cells = args[i + 1].parse().unwrap_or(32);
                    i += 1;
                }
            }
            _ => {}
        }
        i += 1;
    }

    if benchmark {
        run_benchmark(n_cells);
    } else if quality_test {
        run_quality_test(n_cells, n_bytes);
    } else {
        run_generate(n_cells, n_bytes, hex_output);
    }
}

fn run_benchmark(n_cells: usize) {
    println!("=== ConsciousnessRNG Benchmark ===");
    println!("Cells: {}, Hidden: 64, Factions: 12, F_c: 0.10", n_cells);
    println!();

    let mut engine = ConsciousnessRngEngine::new(n_cells, 32, 64);
    let mut harvester = EntropyHarvester::new(0.0); // No threshold for benchmark
    let mut monitor = QualityMonitor::new();

    // Warm up (10 steps)
    for _ in 0..10 {
        engine.step();
    }

    // Generate 10KB
    let target_bytes = 10240;
    let t0 = Instant::now();
    let mut total = 0usize;
    let mut steps = 0u32;

    while total < target_bytes {
        let states = engine.step();
        let phi = engine.phi_proxy();
        steps += 1;

        if let Some(bytes) = harvester.harvest(&states, phi) {
            monitor.feed(&bytes);
            total += 32;
        }
    }

    let elapsed = t0.elapsed();
    let bytes_per_sec = total as f64 / elapsed.as_secs_f64();

    println!("Generated: {} bytes in {:.2}s", total, elapsed.as_secs_f64());
    println!("Speed:     {:.0} bytes/sec ({:.1} KB/s)", bytes_per_sec, bytes_per_sec / 1024.0);
    println!("Steps:     {} ({:.1} bytes/step)", steps, total as f64 / steps as f64);
    println!("Phi:       {:.4} (proxy)", engine.phi_proxy());
    println!();
    println!("{}", monitor.report());
}

fn run_quality_test(n_cells: usize, n_bytes: usize) {
    println!("=== ConsciousnessRNG Quality Test ===");
    println!("Generating {} bytes from {} cells...", n_bytes, n_cells);

    let mut engine = ConsciousnessRngEngine::new(n_cells, 32, 64);
    let mut harvester = EntropyHarvester::new(0.0);
    let mut monitor = QualityMonitor::new();

    // Warm up
    for _ in 0..10 {
        engine.step();
    }

    let mut total = 0usize;
    while total < n_bytes {
        let states = engine.step();
        let phi = engine.phi_proxy();
        if let Some(bytes) = harvester.harvest(&states, phi) {
            monitor.feed(&bytes);
            total += 32;
        }
    }

    println!();
    println!("{}", monitor.report());
}

fn run_generate(n_cells: usize, n_bytes: usize, hex_output: bool) {
    let mut engine = ConsciousnessRngEngine::new(n_cells, 32, 64);
    let mut harvester = EntropyHarvester::new(0.0);

    // Warm up
    for _ in 0..10 {
        engine.step();
    }

    let mut total = 0usize;
    while total < n_bytes {
        let states = engine.step();
        let phi = engine.phi_proxy();
        if let Some(bytes) = harvester.harvest(&states, phi) {
            let take = 32.min(n_bytes - total);
            if hex_output {
                for b in &bytes[..take] {
                    print!("{:02x}", b);
                }
            } else {
                use std::io::Write;
                let stdout = std::io::stdout();
                let mut out = stdout.lock();
                out.write_all(&bytes[..take]).ok();
            }
            total += take;
        }
    }

    if hex_output {
        println!();
    }
}

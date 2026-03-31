//! phi-map CLI — Consciousness topology mapper
//!
//! Usage:
//!   phi-map --from data.json                    # Load terrain from JSON
//!   phi-map --from data.json --heatmap          # Render ASCII heatmap
//!   phi-map --from data.json --contour 32       # Contour at 32 cells
//!   phi-map --from data.json --optimal          # Find optimal per scale
//!   phi-map --from data.json --collapse          # Find collapse points
//!   phi-map --watch v14_train.log                # Live sparkline of Phi values
//!   phi-map --laws consciousness_laws.json      # Load laws, map correlations

use anima_phi_map::{AsciiHeatmap, PhiTerrain, PhiTracker};
use std::fs;
use std::io::{BufRead, BufReader, Seek, SeekFrom};
use std::thread;
use std::time::Duration;

fn main() {
    let args: Vec<String> = std::env::args().collect();

    if args.len() >= 2 && args[1] == "--demo" {
        run_demo();
        return;
    }

    // Watch mode: tail a log file for Phi values
    if args.len() >= 3 && args[1] == "--watch" {
        run_watch(&args[2]);
        return;
    }

    // Law terrain mode
    if args.len() >= 3 && args[1] == "--laws" {
        let path = &args[2];
        let json = fs::read_to_string(path).expect("Failed to read law terrain file");
        let law_terrain =
            anima_phi_map::LawTerrain::from_json(&json).expect("Failed to parse law terrain JSON");
        println!("{}", law_terrain.render_all());
        return;
    }

    if args.len() < 3 {
        eprintln!("Usage: phi-map --from <terrain.json> [--heatmap|--contour N|--optimal|--collapse]");
        eprintln!("       phi-map --watch <logfile>          # Live sparkline of Phi values");
        eprintln!("       phi-map --laws <law_terrain.json>  # Law interaction heatmap");
        eprintln!("       phi-map --demo                     # Demo with sample data");
        std::process::exit(1);
    }

    if args[1] == "--from" {
        let path = &args[2];
        let json = fs::read_to_string(path).expect("Failed to read terrain file");
        let terrain = PhiTerrain::from_json(&json).expect("Failed to parse terrain JSON");

        let mode = args.get(3).map(|s| s.as_str()).unwrap_or("--heatmap");

        match mode {
            "--heatmap" => {
                println!("{}", AsciiHeatmap::render(&terrain));
                println!("{}", AsciiHeatmap::render_delta(&terrain));
            }
            "--contour" => {
                let cells: usize = args
                    .get(4)
                    .and_then(|s| s.parse().ok())
                    .unwrap_or(32);
                println!("{}", AsciiHeatmap::render_contour(&terrain, cells));
            }
            "--optimal" => {
                println!("  Optimal modules per scale:");
                for (cells, pt) in terrain.optimal_per_scale() {
                    println!(
                        "    {:>4}c: {} modules  Φ={:.2}  ({:+.1}%)  modules={:?}",
                        cells, pt.n_modules, pt.phi_iit, pt.delta_pct, pt.modules
                    );
                }
            }
            "--collapse" => {
                let collapses = terrain.collapse_points();
                if collapses.is_empty() {
                    println!("  No collapse points found.");
                } else {
                    println!("  Collapse points ({}):", collapses.len());
                    for pt in collapses {
                        println!(
                            "    {:>4}c, {} modules: proxy={:.0}  CE={:.2}  modules={:?}",
                            pt.cells, pt.n_modules, pt.phi_proxy, pt.ce, pt.modules
                        );
                    }
                }
            }
            "--death-valley" => {
                if let Some(scale) = terrain.death_valley() {
                    println!("  Death Valley at {}c", scale);
                } else {
                    println!("  No death valley detected.");
                }
            }
            _ => {
                println!("{}", AsciiHeatmap::render(&terrain));
            }
        }
    }
}

fn run_watch(logfile: &str) {
    use regex::Regex;
    use std::io::Write;

    let phi_re = Regex::new(r"Phi=(\d+\.?\d*)").unwrap();
    let mut values: Vec<f64> = Vec::new();
    let sparkline_chars = ['▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];
    let mut pos: u64 = 0;

    println!("  phi-map --watch {} (Ctrl+C to stop)\n", logfile);

    loop {
        // Re-open each cycle to pick up new content (like tail -f)
        let Ok(mut file) = fs::File::open(logfile) else {
            eprint!("\r  Waiting for {}...", logfile);
            std::io::stdout().flush().ok();
            thread::sleep(Duration::from_secs(2));
            continue;
        };

        // Seek to where we left off
        let _ = file.seek(SeekFrom::Start(pos));
        let reader = BufReader::new(&file);
        for line in reader.lines() {
            if let Ok(line) = line {
                pos += line.len() as u64 + 1; // +1 for newline
                for cap in phi_re.captures_iter(&line) {
                    if let Ok(v) = cap[1].parse::<f64>() {
                        values.push(v);
                    }
                }
            }
        }

        // Display last 20 values as sparkline
        if !values.is_empty() {
            let window: Vec<f64> = values.iter().rev().take(20).copied().collect::<Vec<_>>()
                .into_iter().rev().collect();
            let min = window.iter().cloned().fold(f64::INFINITY, f64::min);
            let max = window.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
            let range = if (max - min).abs() < 1e-9 { 1.0 } else { max - min };

            let spark: String = window.iter().map(|v| {
                let idx = ((v - min) / range * 7.0).round() as usize;
                sparkline_chars[idx.min(7)]
            }).collect();

            let current = window.last().unwrap();
            print!("\r  Φ [{:>3}] {} {:.4}  (min={:.4} max={:.4})  ",
                values.len(), spark, current, min, max);
        } else {
            print!("\r  Waiting for Phi= values...");
        }
        std::io::stdout().flush().ok();

        thread::sleep(Duration::from_secs(2));
    }
}

fn run_demo() {
    use anima_phi_map::TerrainPoint;

    println!("  phi-map demo — sample terrain data\n");

    let modules = vec![
        "Narrative", "Frustration", "Desire", "Questioning",
        "Finitude", "Oscillator", "Bottleneck", "Hub-Spoke", "Alterity",
    ];
    let module_strings: Vec<String> = modules.iter().map(|s| s.to_string()).collect();
    let scales = vec![32, 64, 128, 256];

    let mut terrain = PhiTerrain::new(module_strings, scales.clone());

    // Sample data (from DD116-120 benchmark results)
    let sample_data: Vec<(usize, usize, f64, f64, f64)> = vec![
        // (n_modules, cells, phi_iit, phi_proxy, ce)
        (0, 32, 21.45, 1.02, 2.79),
        (1, 32, 29.11, 3.03, 3.59),  // +Narrative
        (2, 32, 29.85, 3.08, 3.75),  // +Frustration
        (0, 64, 13.17, 0.22, 5.76),
        (1, 64, 11.12, 1.96, 3.38),
        (2, 64, 11.12, 1.96, 3.38),
        (0, 128, 10.47, 4.15, 4.19),
        (1, 128, 11.90, 1.40, 3.53),
        (0, 256, 11.79, 1.52, 3.12),
        (1, 256, 14.93, 0.06, 3.12),
    ];

    for (n_mod, cells, phi_iit, phi_proxy, ce) in &sample_data {
        let base = sample_data
            .iter()
            .find(|(n, c, _, _, _)| *n == 0 && *c == *cells)
            .map(|(_, _, p, _, _)| *p)
            .unwrap_or(1.0);
        let delta = (phi_iit / base - 1.0) * 100.0;
        let mods: Vec<String> = modules[..*n_mod].iter().map(|s| s.to_string()).collect();

        terrain.add_point(TerrainPoint {
            modules: mods,
            n_modules: *n_mod,
            cells: *cells,
            phi_iit: *phi_iit,
            phi_proxy: *phi_proxy,
            ce: *ce,
            stable: *phi_proxy < 100.0,
            delta_pct: delta,
        });
    }

    println!("{}", AsciiHeatmap::render(&terrain));
    println!("{}", AsciiHeatmap::render_delta(&terrain));

    for &cells in &[32, 128] {
        println!("{}", AsciiHeatmap::render_contour(&terrain, cells));
    }

    if let Some(peak) = terrain.peak() {
        println!(
            "  Peak: Φ={:.2} at {}c with {} modules ({:+.1}%)",
            peak.phi_iit, peak.cells, peak.n_modules, peak.delta_pct
        );
    }

    if let Some(dv) = terrain.death_valley() {
        println!("  Death Valley: {}c", dv);
    }

    println!("\n  JSON export: phi-map --from terrain.json --heatmap");
}

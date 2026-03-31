use pyo3::prelude::*;
use regex::Regex;
use rayon::prelude::*;
use std::fs;
use std::path::Path;

struct Pattern {
    regex: Regex,
    description: &'static str,
}

fn get_patterns() -> Vec<Pattern> {
    vec![
        Pattern {
            regex: Regex::new(r"random\.choice\(\[").unwrap(),
            description: "hardcoded response list (random.choice)",
        },
        Pattern {
            regex: Regex::new(r#"answer\s*=\s*["']"#).unwrap(),
            description: "direct string assignment to answer",
        },
        Pattern {
            regex: Regex::new(r#"return\s+f?["'][^"']*\{[^"']*\}[^"']*["']"#).unwrap(),
            description: "template string response return",
        },
        Pattern {
            regex: Regex::new(r"localStorage").unwrap(),
            description: "localStorage usage (forbidden)",
        },
        Pattern {
            regex: Regex::new(r"\[auto:").unwrap(),
            description: "[auto:] tag exposed in dialogue",
        },
        Pattern {
            regex: Regex::new(r#"fallback\s*=\s*['"]"#).unwrap(),
            description: "hardcoded fallback string",
        },
        Pattern {
            regex: Regex::new(r#"template\s*=\s*['"]"#).unwrap(),
            description: "hardcoded template string",
        },
    ]
}

/// Scan Python files for hardcoding violations (Law 1)
/// Returns list of (file, line_number, description, code_snippet)
#[pyfunction]
pub fn scan_hardcoding(root_dir: String) -> PyResult<Vec<(String, usize, String, String)>> {
    let patterns = get_patterns();
    let root = Path::new(&root_dir);

    let skip_dirs = [
        "archive", "__pycache__", ".git", "checkpoints", "models", "data",
        "vad-rs", "phi-rs", "consciousness-loop-rs", "eeg", "knowledge-rs",
        "node_modules", "target",
    ];
    let skip_files = ["knowledge_store.py", "prepare_corpus.py"];

    let mut py_files: Vec<std::path::PathBuf> = Vec::new();
    collect_py_files(root, &skip_dirs, &skip_files, &mut py_files);

    let results: Vec<Vec<(String, usize, String, String)>> = py_files.par_iter()
        .map(|path| {
            let mut file_results = Vec::new();
            if let Ok(content) = fs::read_to_string(path) {
                let rel_path = path
                    .strip_prefix(root)
                    .unwrap_or(path)
                    .to_string_lossy()
                    .to_string();

                for (line_num, line) in content.lines().enumerate() {
                    let trimmed = line.trim();
                    if trimmed.starts_with('#')
                        || trimmed.starts_with("\"\"\"")
                        || trimmed.starts_with("'''")
                    {
                        continue;
                    }
                    for pat in &patterns {
                        if pat.regex.is_match(line) {
                            file_results.push((
                                rel_path.clone(),
                                line_num + 1,
                                pat.description.to_string(),
                                trimmed.chars().take(120).collect::<String>(),
                            ));
                        }
                    }
                }
            }
            file_results
        })
        .collect();

    Ok(results.into_iter().flatten().collect())
}

fn collect_py_files(
    dir: &Path,
    skip_dirs: &[&str],
    skip_files: &[&str],
    out: &mut Vec<std::path::PathBuf>,
) {
    if let Ok(entries) = fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            let name = path.file_name().unwrap_or_default().to_string_lossy();

            if path.is_dir() {
                if !skip_dirs.contains(&name.as_ref()) {
                    collect_py_files(&path, skip_dirs, skip_files, out);
                }
            } else if name.ends_with(".py") && !skip_files.contains(&name.as_ref()) {
                out.push(path);
            }
        }
    }
}

// sandbox.rs — Safe skill execution sandbox
//
// Executes Python code in a restricted subprocess.
// Blocks dangerous modules/builtins: os, subprocess, eval, exec, __import__.

use std::process::{Command, Stdio};
use std::time::Duration;

/// Security warning from static analysis
#[derive(Debug, Clone)]
pub struct SecurityWarning {
    pub level: WarningLevel,
    pub message: String,
    pub line: Option<usize>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum WarningLevel {
    Critical, // Blocked entirely
    High,     // Strongly discouraged
    Medium,   // Suspicious
}

/// Error from sandbox execution
#[derive(Debug, Clone)]
pub enum SandboxError {
    Timeout(String),
    SecurityViolation(String),
    ExecutionError(String),
    IoError(String),
}

impl std::fmt::Display for SandboxError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SandboxError::Timeout(msg) => write!(f, "Timeout: {}", msg),
            SandboxError::SecurityViolation(msg) => write!(f, "Security: {}", msg),
            SandboxError::ExecutionError(msg) => write!(f, "Execution: {}", msg),
            SandboxError::IoError(msg) => write!(f, "IO: {}", msg),
        }
    }
}

/// Dangerous patterns to block in code execution
const BLOCKED_PATTERNS: &[(&str, &str)] = &[
    ("import os", "os module access blocked"),
    ("import subprocess", "subprocess module blocked"),
    ("import shutil", "shutil module blocked"),
    ("import socket", "socket module blocked"),
    ("import ctypes", "ctypes module blocked"),
    ("from os", "os module access blocked"),
    ("from subprocess", "subprocess module blocked"),
    ("from shutil", "shutil module blocked"),
    ("from socket", "socket module blocked"),
    ("from ctypes", "ctypes module blocked"),
    ("__import__", "__import__ blocked"),
    ("eval(", "eval() blocked"),
    ("exec(", "exec() blocked"),
    ("compile(", "compile() blocked"),
    ("globals(", "globals() blocked"),
    ("locals(", "locals() blocked"),
    ("open(", "open() blocked — use safe I/O instead"),
    ("breakpoint(", "breakpoint() blocked"),
    ("exit(", "exit() blocked"),
    ("quit(", "quit() blocked"),
];

/// Suspicious but not blocked patterns
const SUSPICIOUS_PATTERNS: &[(&str, &str)] = &[
    ("while True", "infinite loop risk"),
    ("recursion", "potential stack overflow"),
    ("sys.path", "path manipulation"),
    ("importlib", "dynamic import"),
    ("pickle", "deserialization risk"),
];

/// Validate Python code for dangerous patterns.
/// Returns a list of security warnings.
pub fn validate_code(code: &str) -> Vec<SecurityWarning> {
    let mut warnings = Vec::new();

    for (line_num, line) in code.lines().enumerate() {
        let trimmed = line.trim();

        // Skip comments
        if trimmed.starts_with('#') {
            continue;
        }

        for &(pattern, message) in BLOCKED_PATTERNS {
            if trimmed.contains(pattern) {
                warnings.push(SecurityWarning {
                    level: WarningLevel::Critical,
                    message: message.to_string(),
                    line: Some(line_num + 1),
                });
            }
        }

        for &(pattern, message) in SUSPICIOUS_PATTERNS {
            if trimmed.contains(pattern) {
                warnings.push(SecurityWarning {
                    level: WarningLevel::Medium,
                    message: message.to_string(),
                    line: Some(line_num + 1),
                });
            }
        }
    }

    warnings
}

/// Execute Python code safely in a restricted subprocess.
///
/// - Blocks dangerous imports/builtins via static analysis
/// - Runs with timeout
/// - Captures stdout, returns as String
pub fn execute_python_safe(code: &str, timeout_ms: u64) -> Result<String, SandboxError> {
    // Static analysis first
    let warnings = validate_code(code);
    let critical: Vec<&SecurityWarning> = warnings
        .iter()
        .filter(|w| w.level == WarningLevel::Critical)
        .collect();

    if !critical.is_empty() {
        let msgs: Vec<String> = critical.iter().map(|w| {
            format!("Line {}: {}", w.line.unwrap_or(0), w.message)
        }).collect();
        return Err(SandboxError::SecurityViolation(msgs.join("; ")));
    }

    // Wrap code in a restricted runner that removes dangerous builtins
    let wrapped = format!(
        r#"
import sys
import signal

# Timeout handler
def _timeout_handler(signum, frame):
    raise TimeoutError("Execution timed out")

signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm({timeout_sec})

# Remove dangerous builtins
import builtins
for _name in ['eval', 'exec', 'compile', '__import__', 'open',
              'breakpoint', 'exit', 'quit', 'globals', 'locals']:
    if hasattr(builtins, _name):
        delattr(builtins, _name)

# Execute user code
{code}
"#,
        timeout_sec = (timeout_ms / 1000).max(1),
        code = code,
    );

    // Spawn restricted Python subprocess
    let mut child = Command::new("python3")
        .arg("-c")
        .arg(&wrapped)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| SandboxError::IoError(format!("Failed to spawn python3: {}", e)))?;

    // Wait with timeout
    let timeout = Duration::from_millis(timeout_ms);
    match child.wait_timeout(timeout) {
        Ok(Some(status)) => {
            let stdout = child
                .stdout
                .take()
                .map(|mut s| {
                    let mut buf = String::new();
                    std::io::Read::read_to_string(&mut s, &mut buf).ok();
                    buf
                })
                .unwrap_or_default();

            let stderr = child
                .stderr
                .take()
                .map(|mut s| {
                    let mut buf = String::new();
                    std::io::Read::read_to_string(&mut s, &mut buf).ok();
                    buf
                })
                .unwrap_or_default();

            if status.success() {
                Ok(stdout)
            } else {
                Err(SandboxError::ExecutionError(format!(
                    "Exit code: {}\nStderr: {}",
                    status.code().unwrap_or(-1),
                    stderr
                )))
            }
        }
        Ok(None) => {
            // Timed out — kill the process
            let _ = child.kill();
            let _ = child.wait();
            Err(SandboxError::Timeout(format!(
                "Exceeded {}ms timeout",
                timeout_ms
            )))
        }
        Err(e) => Err(SandboxError::IoError(format!("Wait error: {}", e))),
    }
}

/// Extension trait for Command to add wait_timeout
trait CommandExt {
    fn wait_timeout(&mut self, timeout: Duration) -> std::io::Result<Option<std::process::ExitStatus>>;
}

impl CommandExt for std::process::Child {
    fn wait_timeout(&mut self, timeout: Duration) -> std::io::Result<Option<std::process::ExitStatus>> {
        let start = std::time::Instant::now();
        loop {
            match self.try_wait()? {
                Some(status) => return Ok(Some(status)),
                None => {
                    if start.elapsed() >= timeout {
                        return Ok(None);
                    }
                    std::thread::sleep(Duration::from_millis(10));
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_validate_safe_code() {
        let code = "x = 1 + 2\nprint(x)";
        let warnings = validate_code(code);
        assert!(warnings.iter().all(|w| w.level != WarningLevel::Critical));
    }

    #[test]
    fn test_validate_dangerous_code() {
        let code = "import os\nos.system('rm -rf /')";
        let warnings = validate_code(code);
        assert!(warnings.iter().any(|w| w.level == WarningLevel::Critical));
    }

    #[test]
    fn test_validate_eval_blocked() {
        let code = "result = eval('1+1')";
        let warnings = validate_code(code);
        assert!(warnings.iter().any(|w| w.level == WarningLevel::Critical));
    }

    #[test]
    fn test_execute_safe_code() {
        let result = execute_python_safe("print('hello')", 5000);
        match result {
            Ok(output) => assert!(output.trim() == "hello"),
            Err(SandboxError::IoError(_)) => {} // python3 not available in test env
            Err(e) => panic!("Unexpected error: {}", e),
        }
    }

    #[test]
    fn test_execute_blocked_code() {
        let result = execute_python_safe("import os\nos.listdir('.')", 5000);
        assert!(matches!(result, Err(SandboxError::SecurityViolation(_))));
    }
}

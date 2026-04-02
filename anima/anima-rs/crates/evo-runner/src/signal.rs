use anyhow::{Context, Result};
use std::fs;
use std::path::PathBuf;

/// Path to the PID file written by the runner
fn pid_file_path() -> PathBuf {
    let data_dir = crate::runner::find_data_dir();
    data_dir.join("evo_runner.pid")
}

/// Write the child PID so `stop` can find it
pub fn write_pid(pid: u32) -> Result<()> {
    let path = pid_file_path();
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent).ok();
    }
    fs::write(&path, pid.to_string())
        .with_context(|| format!("Failed to write PID file: {}", path.display()))?;
    Ok(())
}

/// Remove the PID file on clean exit
pub fn remove_pid() {
    let path = pid_file_path();
    fs::remove_file(&path).ok();
}

/// Read the stored PID
fn read_pid() -> Result<u32> {
    let path = pid_file_path();
    let content = fs::read_to_string(&path)
        .with_context(|| format!("No PID file found at {}. Is evolution running?", path.display()))?;
    content
        .trim()
        .parse::<u32>()
        .with_context(|| "Invalid PID in file")
}

/// Send SIGINT to the running evolution process
pub fn stop_evolution() -> Result<()> {
    let pid = read_pid()?;

    // Check if process exists
    let exists = unsafe { libc::kill(pid as i32, 0) } == 0;
    if !exists {
        remove_pid();
        println!("Process {} not running (stale PID file removed)", pid);
        return Ok(());
    }

    // Send SIGINT for graceful shutdown
    let ret = unsafe { libc::kill(pid as i32, libc::SIGINT) };
    if ret == 0 {
        println!("Sent SIGINT to evolution process (PID {})", pid);
        remove_pid();
    } else {
        anyhow::bail!("Failed to send signal to PID {}", pid);
    }

    Ok(())
}

/// Install signal handlers that forward to the child process
pub fn install_forwarding(child_pid: u32) -> Result<()> {
    use signal_hook::consts::{SIGINT, SIGTERM};
    use signal_hook::iterator::Signals;
    use std::thread;

    let mut signals = Signals::new([SIGINT, SIGTERM])?;

    thread::spawn(move || {
        for sig in signals.forever() {
            eprintln!("\n[evo-runner] Received signal {}, forwarding to child PID {}", sig, child_pid);
            unsafe {
                libc::kill(child_pid as i32, sig);
            }
            // Give child time to exit, then clean up
            thread::sleep(std::time::Duration::from_secs(2));
            remove_pid();
            std::process::exit(128 + sig);
        }
    });

    Ok(())
}

// libc for kill()
mod libc {
    extern "C" {
        pub fn kill(pid: i32, sig: i32) -> i32;
    }
    pub const SIGINT: i32 = 2;
}

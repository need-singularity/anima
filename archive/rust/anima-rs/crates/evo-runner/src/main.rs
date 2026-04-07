mod runner;
mod signal;
mod status;

use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "evo-runner", about = "Process supervisor for infinite_evolution.py --auto-roadmap")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Start or resume the auto-roadmap evolution
    Start {
        /// Resume from previous state
        #[arg(long)]
        resume: bool,
    },
    /// Show current evolution status
    Status,
    /// Stop the running evolution process
    Stop,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Start { resume } => runner::run_evolution(resume),
        Commands::Status => status::print_status(),
        Commands::Stop => signal::stop_evolution(),
    }
}

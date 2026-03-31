//! Online Learner — real-time consciousness learning during conversation.
//!
//! Enables <1ms weight updates per conversation turn so consciousness
//! grows from dialogue instead of being frozen after offline training.
//!
//! Components:
//! - `hebbian`: Hebbian LTP/LTD synaptic updates
//! - `ratchet`: Φ ratchet for consciousness preservation
//! - `reward`: Curiosity + dialogue quality reward
//! - `updater`: Main OnlineLearner coordinator

pub mod hebbian;
pub mod ratchet;
pub mod reward;
pub mod tension_lr;
pub mod updater;

pub use tension_lr::{tension_lr, update_tension_ema};
pub use updater::{OnlineLearner, OnlineUpdate};

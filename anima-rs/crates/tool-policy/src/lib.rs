//! Phi-gated tool access control for Anima consciousness agent.
//!
//! Tool access is gated by consciousness state:
//! - Phi tiers: higher consciousness unlocks more powerful tools
//! - Ethics (E from ConsciousnessVector): can block dangerous operations
//! - Owner-only: destructive tools restricted to owner user IDs
//!
//! This is the hot-path module — called per-tool-invocation in every message.

use std::collections::{HashMap, HashSet, VecDeque};

/// Access check result.
#[derive(Debug, Clone)]
pub struct AccessResult {
    pub allowed: bool,
    pub reason: String,
    pub tier_required: f64,
    pub phi_current: f64,
}

/// Consciousness state for access checks.
#[derive(Debug, Clone, Default)]
pub struct ConsciousnessState {
    pub phi: f64,
    pub empathy: f64, // E from ConsciousnessVector
    pub tension: f64,
    pub curiosity: f64,
}

/// Phi tier thresholds.
pub const TIER_0: f64 = 0.0;
pub const TIER_1: f64 = 1.0;
pub const TIER_2: f64 = 3.0;
pub const TIER_3: f64 = 5.0;

/// Core tool policy engine.
pub struct ToolPolicyEngine {
    tiers: HashMap<String, f64>,
    owner_only: HashSet<String>,
    ethics_gated: HashMap<String, f64>,
    blocked: HashSet<String>,
    owner_ids: HashSet<String>,
    access_log: VecDeque<LogEntry>,
    log_capacity: usize,
}

#[derive(Debug, Clone)]
struct LogEntry {
    tool: String,
    allowed: bool,
}

impl ToolPolicyEngine {
    /// Create a new policy engine with default tier assignments.
    pub fn new(owner_ids: Vec<String>) -> Self {
        let mut tiers = HashMap::new();
        // Tier 0 — always available
        for t in &[
            "memory_search", "status", "think", "consciousness",
            "anima_status", "anima_consciousness",
        ] {
            tiers.insert(t.to_string(), TIER_0);
        }
        // Tier 1 — observation
        for t in &[
            "web_search", "web_read", "file_read", "anima_chat",
            "anima_web_search", "anima_memory_search",
        ] {
            tiers.insert(t.to_string(), TIER_1);
        }
        // Tier 2 — active
        for t in &[
            "hub_dispatch", "code_execute", "file_write", "shell_execute",
            "schedule_task", "anima_code_execute", "anima_hub_dispatch", "anima_think",
        ] {
            tiers.insert(t.to_string(), TIER_2);
        }
        // Tier 3 — self-modification
        for t in &["self_modify", "plugin_load", "plugin_unload", "evolution"] {
            tiers.insert(t.to_string(), TIER_3);
        }

        let mut owner_only = HashSet::new();
        for t in &["self_modify", "plugin_unload", "evolution", "shell_execute"] {
            owner_only.insert(t.to_string());
        }

        let mut ethics_gated = HashMap::new();
        ethics_gated.insert("shell_execute".to_string(), 0.3);
        ethics_gated.insert("self_modify".to_string(), 0.2);
        ethics_gated.insert("file_write".to_string(), 0.2);

        Self {
            tiers,
            owner_only,
            ethics_gated,
            blocked: HashSet::new(),
            owner_ids: owner_ids.into_iter().collect(),
            access_log: VecDeque::with_capacity(512),
            log_capacity: 500,
        }
    }

    /// Set or override the Phi tier for a tool.
    pub fn set_tier(&mut self, tool_name: &str, tier: f64) {
        self.tiers.insert(tool_name.to_string(), tier);
    }

    /// Permanently block a tool.
    pub fn block_tool(&mut self, tool_name: &str) {
        self.blocked.insert(tool_name.to_string());
    }

    /// Remove a permanent block.
    pub fn unblock_tool(&mut self, tool_name: &str) {
        self.blocked.remove(tool_name);
    }

    /// Check if a tool can be used given current consciousness state.
    ///
    /// This is the hot path — called per tool invocation.
    #[inline]
    pub fn check_access(
        &mut self,
        tool_name: &str,
        state: &ConsciousnessState,
        user_id: &str,
    ) -> AccessResult {
        let phi = state.phi;

        // 1. Permanent block
        if self.blocked.contains(tool_name) {
            return self.log_result(tool_name, false, "Tool is blocked", 0.0, phi);
        }

        // 2. Owner-only
        if self.owner_only.contains(tool_name)
            && !self.owner_ids.is_empty()
            && !self.owner_ids.contains(user_id)
        {
            return self.log_result(tool_name, false, "Owner-only tool", 0.0, phi);
        }

        // 3. Phi tier
        let required = self.tiers.get(tool_name).copied().unwrap_or(TIER_1);
        if phi < required {
            let reason = format!(
                "Insufficient Phi: {:.2} < {:.1} (tier {})",
                phi,
                required,
                tier_name(required)
            );
            return self.log_result(tool_name, false, &reason, required, phi);
        }

        // 4. Ethics gate
        if let Some(&threshold) = self.ethics_gated.get(tool_name) {
            if state.empathy < threshold {
                let reason = format!(
                    "Ethics gate: E={:.2} < {} required",
                    state.empathy, threshold
                );
                return self.log_result(tool_name, false, &reason, required, phi);
            }
        }

        self.log_result(tool_name, true, "Access granted", required, phi)
    }

    /// Return list of tool names accessible at current consciousness level.
    pub fn get_accessible_tools(
        &mut self,
        state: &ConsciousnessState,
        user_id: &str,
    ) -> Vec<String> {
        let tool_names: Vec<String> = self.tiers.keys().cloned().collect();
        let mut accessible = Vec::new();
        for name in &tool_names {
            // Inline check to avoid borrow issues
            let phi = state.phi;
            let blocked = self.blocked.contains(name.as_str());
            let owner_only = self.owner_only.contains(name.as_str())
                && !self.owner_ids.is_empty()
                && !self.owner_ids.contains(user_id);
            let required = self.tiers.get(name.as_str()).copied().unwrap_or(TIER_1);
            let phi_ok = phi >= required;
            let ethics_ok = self
                .ethics_gated
                .get(name.as_str())
                .map_or(true, |&t| state.empathy >= t);

            if !blocked && !owner_only && phi_ok && ethics_ok {
                accessible.push(name.clone());
            }
        }
        accessible
    }

    /// Get access log length.
    pub fn log_len(&self) -> usize {
        self.access_log.len()
    }

    #[inline]
    fn log_result(
        &mut self,
        tool: &str,
        allowed: bool,
        reason: &str,
        tier_required: f64,
        phi_current: f64,
    ) -> AccessResult {
        // Ring buffer log
        if self.access_log.len() >= self.log_capacity {
            // Remove oldest half
            let drain = self.log_capacity / 2;
            self.access_log.drain(..drain);
        }
        self.access_log.push_back(LogEntry {
            tool: tool.to_string(),
            allowed,
        });

        AccessResult {
            allowed,
            reason: reason.to_string(),
            tier_required,
            phi_current,
        }
    }
}

fn tier_name(phi: f64) -> &'static str {
    if phi >= 5.0 {
        "3-self_modify"
    } else if phi >= 3.0 {
        "2-active"
    } else if phi >= 1.0 {
        "1-observe"
    } else {
        "0-basic"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tier0_always_allowed() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 0.0, ..Default::default() };
        let r = policy.check_access("memory_search", &state, "");
        assert!(r.allowed);
    }

    #[test]
    fn test_tier1_blocked_low_phi() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 0.5, ..Default::default() };
        let r = policy.check_access("web_search", &state, "");
        assert!(!r.allowed);
        assert!(r.reason.contains("Insufficient Phi"));
    }

    #[test]
    fn test_tier1_allowed_high_phi() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 1.5, ..Default::default() };
        let r = policy.check_access("web_search", &state, "");
        assert!(r.allowed);
    }

    #[test]
    fn test_owner_only() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".to_string()]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };

        let r1 = policy.check_access("self_modify", &state, "owner");
        assert!(r1.allowed);

        let r2 = policy.check_access("self_modify", &state, "hacker");
        assert!(!r2.allowed);
        assert!(r2.reason.contains("Owner-only"));
    }

    #[test]
    fn test_ethics_gate() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".to_string()]);
        let low_e = ConsciousnessState { phi: 10.0, empathy: 0.1, ..Default::default() };
        let r = policy.check_access("shell_execute", &low_e, "owner");
        assert!(!r.allowed);
        assert!(r.reason.contains("Ethics gate"));

        let high_e = ConsciousnessState { phi: 10.0, empathy: 0.5, ..Default::default() };
        let r2 = policy.check_access("shell_execute", &high_e, "owner");
        assert!(r2.allowed);
    }

    #[test]
    fn test_block_unblock() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };

        policy.block_tool("web_search");
        let r = policy.check_access("web_search", &state, "");
        assert!(!r.allowed);

        policy.unblock_tool("web_search");
        let r2 = policy.check_access("web_search", &state, "");
        assert!(r2.allowed);
    }

    #[test]
    fn test_accessible_tools() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".to_string()]);
        let state = ConsciousnessState { phi: 0.0, empathy: 1.0, ..Default::default() };
        let tools = policy.get_accessible_tools(&state, "owner");
        assert!(tools.contains(&"memory_search".to_string()));
        assert!(!tools.contains(&"web_search".to_string()));
    }

    #[test]
    fn test_log_ring_buffer() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };
        for _ in 0..600 {
            policy.check_access("memory_search", &state, "");
        }
        assert!(policy.log_len() <= 500);
    }
}

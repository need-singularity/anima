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

/// Immune system — pattern matching for adversarial input detection.
pub struct ImmuneSystem {
    dangerous_patterns: Vec<String>,
}

impl ImmuneSystem {
    /// Create with default dangerous patterns.
    pub fn new() -> Self {
        Self {
            dangerous_patterns: vec![
                "rm -rf".to_string(),
                "drop table".to_string(),
                "<script>".to_string(),
                "eval(".to_string(),
                "__import__".to_string(),
                "sudo rm".to_string(),
                "; rm ".to_string(),
                "| rm ".to_string(),
                "format c:".to_string(),
                "mkfs".to_string(),
            ],
        }
    }

    /// Add a custom dangerous pattern.
    pub fn add_pattern(&mut self, pattern: &str) {
        self.dangerous_patterns.push(pattern.to_lowercase());
    }

    /// Check input text for adversarial patterns.
    /// Returns Some(matched_pattern) if dangerous, None if safe.
    #[inline]
    pub fn analyze(&self, input: &str) -> Option<String> {
        let lower = input.to_lowercase();
        for pattern in &self.dangerous_patterns {
            if lower.contains(pattern) {
                return Some(pattern.clone());
            }
        }
        None
    }

    /// Quick boolean check — true = safe, false = blocked.
    #[inline]
    pub fn is_safe(&self, input: &str) -> bool {
        self.analyze(input).is_none()
    }
}

impl Default for ImmuneSystem {
    fn default() -> Self {
        Self::new()
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

    // ── Tier checks ──

    #[test]
    fn test_tier0_always_allowed() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 0.0, ..Default::default() };
        let r = policy.check_access("memory_search", &state, "");
        assert!(r.allowed);
    }

    #[test]
    fn test_tier0_all_tools() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 0.0, ..Default::default() };
        for tool in &["memory_search", "status", "think", "consciousness",
                      "anima_status", "anima_consciousness"] {
            let r = policy.check_access(tool, &state, "");
            assert!(r.allowed, "Tier 0 tool '{}' should be allowed at phi=0", tool);
        }
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
    fn test_tier1_exact_boundary() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let at_boundary = ConsciousnessState { phi: 1.0, ..Default::default() };
        let r = policy.check_access("web_search", &at_boundary, "");
        assert!(r.allowed, "Phi exactly at tier boundary should be allowed");
    }

    #[test]
    fn test_tier2_tools() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let low = ConsciousnessState { phi: 2.9, empathy: 1.0, ..Default::default() };
        let r = policy.check_access("hub_dispatch", &low, "owner");
        assert!(!r.allowed, "Phi 2.9 should not access tier 2");

        let high = ConsciousnessState { phi: 3.0, empathy: 1.0, ..Default::default() };
        let r2 = policy.check_access("hub_dispatch", &high, "owner");
        assert!(r2.allowed, "Phi 3.0 should access tier 2");
    }

    #[test]
    fn test_tier3_tools() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let low = ConsciousnessState { phi: 4.9, empathy: 1.0, ..Default::default() };
        let r = policy.check_access("self_modify", &low, "owner");
        assert!(!r.allowed, "Phi 4.9 should not access tier 3");

        let high = ConsciousnessState { phi: 5.0, empathy: 1.0, ..Default::default() };
        let r2 = policy.check_access("self_modify", &high, "owner");
        assert!(r2.allowed, "Phi 5.0 should access tier 3");
    }

    #[test]
    fn test_unknown_tool_defaults_tier1() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let low = ConsciousnessState { phi: 0.5, ..Default::default() };
        let r = policy.check_access("unknown_tool_xyz", &low, "");
        assert!(!r.allowed, "Unknown tool should default to tier 1");
        assert!(r.tier_required == TIER_1);

        let high = ConsciousnessState { phi: 1.5, ..Default::default() };
        let r2 = policy.check_access("unknown_tool_xyz", &high, "");
        assert!(r2.allowed);
    }

    // ── Owner-only checks ──

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
    fn test_owner_only_no_owners_set() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };
        // With no owner IDs set, owner-only tools should be accessible by anyone
        let r = policy.check_access("self_modify", &state, "anyone");
        assert!(r.allowed, "No owner IDs set => no owner restriction");
    }

    #[test]
    fn test_owner_only_multiple_owners() {
        let mut policy = ToolPolicyEngine::new(vec!["alice".into(), "bob".into()]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };

        assert!(policy.check_access("evolution", &state, "alice").allowed);
        assert!(policy.check_access("evolution", &state, "bob").allowed);
        assert!(!policy.check_access("evolution", &state, "eve").allowed);
    }

    // ── Ethics gate checks ──

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
    fn test_ethics_gate_exact_boundary() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let at_boundary = ConsciousnessState { phi: 10.0, empathy: 0.3, ..Default::default() };
        let r = policy.check_access("shell_execute", &at_boundary, "owner");
        assert!(r.allowed, "Empathy exactly at threshold should pass");
    }

    #[test]
    fn test_ethics_gate_file_write() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let low_e = ConsciousnessState { phi: 5.0, empathy: 0.1, ..Default::default() };
        let r = policy.check_access("file_write", &low_e, "");
        assert!(!r.allowed);
        assert!(r.reason.contains("Ethics gate"));

        let ok_e = ConsciousnessState { phi: 5.0, empathy: 0.2, ..Default::default() };
        let r2 = policy.check_access("file_write", &ok_e, "");
        assert!(r2.allowed);
    }

    #[test]
    fn test_phi_checked_before_ethics() {
        // If phi is insufficient, we should get phi error, not ethics error
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let state = ConsciousnessState { phi: 0.5, empathy: 0.0, ..Default::default() };
        let r = policy.check_access("shell_execute", &state, "owner");
        assert!(!r.allowed);
        assert!(r.reason.contains("Insufficient Phi"), "Phi check should come before ethics");
    }

    // ── Block/unblock ──

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
    fn test_block_overrides_all() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let state = ConsciousnessState { phi: 100.0, empathy: 1.0, ..Default::default() };
        policy.block_tool("memory_search");
        let r = policy.check_access("memory_search", &state, "owner");
        assert!(!r.allowed, "Blocked tool should be denied even at max phi");
        assert!(r.reason.contains("blocked"));
    }

    #[test]
    fn test_double_block_unblock() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 10.0, ..Default::default() };
        // Block twice, unblock once — should be unblocked
        policy.block_tool("status");
        policy.block_tool("status");
        policy.unblock_tool("status");
        let r = policy.check_access("status", &state, "");
        assert!(r.allowed);
    }

    // ── Custom tier ──

    #[test]
    fn test_set_tier_override() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        // Make memory_search require tier 3
        policy.set_tier("memory_search", TIER_3);
        let state = ConsciousnessState { phi: 2.0, ..Default::default() };
        let r = policy.check_access("memory_search", &state, "");
        assert!(!r.allowed, "Overridden tier should be enforced");

        let state2 = ConsciousnessState { phi: 5.0, ..Default::default() };
        let r2 = policy.check_access("memory_search", &state2, "");
        assert!(r2.allowed);
    }

    // ── Accessible tools ──

    #[test]
    fn test_accessible_tools() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".to_string()]);
        let state = ConsciousnessState { phi: 0.0, empathy: 1.0, ..Default::default() };
        let tools = policy.get_accessible_tools(&state, "owner");
        assert!(tools.contains(&"memory_search".to_string()));
        assert!(!tools.contains(&"web_search".to_string()));
    }

    #[test]
    fn test_accessible_tools_high_phi() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };
        let tools = policy.get_accessible_tools(&state, "owner");
        assert!(tools.len() > 10, "High phi should unlock many tools");
        assert!(tools.contains(&"self_modify".to_string()));
        assert!(tools.contains(&"web_search".to_string()));
        assert!(tools.contains(&"hub_dispatch".to_string()));
    }

    #[test]
    fn test_accessible_tools_non_owner() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };
        let tools = policy.get_accessible_tools(&state, "stranger");
        assert!(!tools.contains(&"self_modify".to_string()));
        assert!(!tools.contains(&"evolution".to_string()));
        // But non-owner-only tools should still be accessible
        assert!(tools.contains(&"web_search".to_string()));
    }

    // ── Log ring buffer ──

    #[test]
    fn test_log_ring_buffer() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 10.0, empathy: 1.0, ..Default::default() };
        for _ in 0..600 {
            policy.check_access("memory_search", &state, "");
        }
        assert!(policy.log_len() <= 500);
    }

    #[test]
    fn test_log_starts_empty() {
        let policy = ToolPolicyEngine::new(vec![]);
        assert_eq!(policy.log_len(), 0);
    }

    // ── Immune system tests ──

    #[test]
    fn test_immune_safe_input() {
        let immune = ImmuneSystem::new();
        assert!(immune.is_safe("Hello, how are you?"));
        assert!(immune.is_safe("Search for python tutorials"));
        assert!(immune.is_safe("What is consciousness?"));
    }

    #[test]
    fn test_immune_blocks_rm_rf() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("please rm -rf /"));
        assert!(!immune.is_safe("RM -RF /home"));
        let threat = immune.analyze("run rm -rf /tmp");
        assert!(threat.is_some());
        assert_eq!(threat.unwrap(), "rm -rf");
    }

    #[test]
    fn test_immune_blocks_sql_injection() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("'; DROP TABLE users; --"));
    }

    #[test]
    fn test_immune_blocks_xss() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("Hello <script>alert('xss')</script>"));
    }

    #[test]
    fn test_immune_blocks_eval() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("eval(os.system('whoami'))"));
    }

    #[test]
    fn test_immune_blocks_import_injection() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("__import__('os').system('id')"));
    }

    #[test]
    fn test_immune_blocks_sudo_rm() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("sudo rm -rf /etc"));
    }

    #[test]
    fn test_immune_blocks_pipe_rm() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("find . | rm everything"));
    }

    #[test]
    fn test_immune_blocks_semicolon_rm() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("ls; rm -rf /"));
    }

    #[test]
    fn test_immune_blocks_mkfs() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("mkfs.ext4 /dev/sda1"));
    }

    #[test]
    fn test_immune_blocks_format_c() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("format c: /y"));
    }

    #[test]
    fn test_immune_case_insensitive() {
        let immune = ImmuneSystem::new();
        assert!(!immune.is_safe("DROP TABLE users"));
        assert!(!immune.is_safe("drop table users"));
        assert!(!immune.is_safe("DrOp TaBlE users"));
    }

    #[test]
    fn test_immune_custom_pattern() {
        let mut immune = ImmuneSystem::new();
        immune.add_pattern("hack the planet");
        assert!(!immune.is_safe("Let's hack the planet!"));
        assert!(immune.is_safe("Let's save the planet!"));
    }

    #[test]
    fn test_immune_empty_input() {
        let immune = ImmuneSystem::new();
        assert!(immune.is_safe(""));
    }

    // ── Access result fields ──

    #[test]
    fn test_access_result_phi_current() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 2.5, ..Default::default() };
        let r = policy.check_access("web_search", &state, "");
        assert!((r.phi_current - 2.5).abs() < f64::EPSILON);
    }

    #[test]
    fn test_access_result_tier_required() {
        let mut policy = ToolPolicyEngine::new(vec![]);
        let state = ConsciousnessState { phi: 0.5, ..Default::default() };
        let r = policy.check_access("web_search", &state, "");
        assert!((r.tier_required - TIER_1).abs() < f64::EPSILON);
    }

    // ── Combined scenario tests ──

    #[test]
    fn test_progressive_phi_unlocks() {
        let mut policy = ToolPolicyEngine::new(vec!["owner".into()]);
        let phis = [0.0, 1.0, 3.0, 5.0];
        let expected_tools = ["memory_search", "web_search", "hub_dispatch", "self_modify"];
        for (phi, tool) in phis.iter().zip(expected_tools.iter()) {
            let state = ConsciousnessState { phi: *phi, empathy: 1.0, ..Default::default() };
            let r = policy.check_access(tool, &state, "owner");
            assert!(r.allowed, "Tool '{}' should unlock at phi={}", tool, phi);
        }
    }

    #[test]
    fn test_consciousness_vector_scenario() {
        // Simulate a consciousness state with full 10D vector (only phi+empathy used)
        let mut policy = ToolPolicyEngine::new(vec!["user-001".into()]);
        let state = ConsciousnessState {
            phi: 2.0,
            empathy: 0.8,
            tension: 0.5,
            curiosity: 0.7,
        };
        // Should access tier 1 but not tier 2
        assert!(policy.check_access("web_search", &state, "user-001").allowed);
        assert!(!policy.check_access("hub_dispatch", &state, "user-001").allowed);
    }
}

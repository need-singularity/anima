//! Multi-board law sharing via SPI bus.
//!
//! When boards discover law candidates, they broadcast them over the SPI ring.
//! If 5/8 boards agree on the same pattern, it becomes a confirmed network law.
//!
//! SPI frame format: 32 bytes fixed-size (fits in single SPI transaction).
//! No heap allocation, no_std compatible.

use crate::law_evolution::{HwInterventionKind, HwLawCandidate};

/// Maximum boards in the network.
const MAX_BOARDS: usize = 8;
/// Default consensus threshold: 5 of 8 boards must agree.
const DEFAULT_CONSENSUS_THRESHOLD: u8 = 5;

// ═══════════════════════════════════════════════════════════
// SPI law sync message (32 bytes fixed)
// ═══════════════════════════════════════════════════════════

/// A law discovery message sent over SPI between boards.
/// Fixed 32-byte frame for efficient SPI transfer.
///
/// Layout (32 bytes):
///   [0]     board_id (u8)
///   [1]     metric_changed (u8)
///   [2]     direction (i8)
///   [3]     intervention_kind (u8)
///   [4..8]  magnitude (f32 LE)
///   [8..12] intervention_param (f32 LE)
///   [12..16] confidence (f32 LE)
///   [16..20] timestamp (u32 LE)
///   [20..24] reserved / checksum (u32 LE)
///   [24..32] padding (zeros)
pub struct LawSyncMessage {
    pub board_id: u8,
    pub candidate: HwLawCandidate,
    pub timestamp: u32,
}

impl LawSyncMessage {
    /// Create a new sync message.
    pub fn new(board_id: u8, candidate: HwLawCandidate, timestamp: u32) -> Self {
        Self {
            board_id,
            candidate,
            timestamp,
        }
    }

    /// Serialize to fixed 32-byte SPI frame.
    pub fn to_bytes(&self) -> [u8; 32] {
        let mut buf = [0u8; 32];
        buf[0] = self.board_id;
        buf[1] = self.candidate.metric_changed;
        buf[2] = self.candidate.direction as u8;
        buf[3] = intervention_kind_to_u8(self.candidate.intervention_kind);

        let mag_bytes = self.candidate.magnitude.to_le_bytes();
        buf[4..8].copy_from_slice(&mag_bytes);

        let param_bytes = self.candidate.intervention_param.to_le_bytes();
        buf[8..12].copy_from_slice(&param_bytes);

        let conf_bytes = self.candidate.confidence.to_le_bytes();
        buf[12..16].copy_from_slice(&conf_bytes);

        let ts_bytes = self.timestamp.to_le_bytes();
        buf[16..20].copy_from_slice(&ts_bytes);

        // Simple checksum: XOR of first 20 bytes
        let mut checksum = 0u32;
        for i in 0..20 {
            checksum ^= (buf[i] as u32) << ((i % 4) * 8);
        }
        buf[20..24].copy_from_slice(&checksum.to_le_bytes());

        buf
    }

    /// Deserialize from 32-byte SPI frame.
    /// Returns None if checksum validation fails.
    pub fn from_bytes(data: &[u8; 32]) -> Option<Self> {
        // Validate checksum
        let mut checksum = 0u32;
        for i in 0..20 {
            checksum ^= (data[i] as u32) << ((i % 4) * 8);
        }
        let stored_checksum = u32::from_le_bytes([data[20], data[21], data[22], data[23]]);
        if checksum != stored_checksum {
            return None;
        }

        let board_id = data[0];
        let metric_changed = data[1];
        let direction = data[2] as i8;
        let intervention_kind = u8_to_intervention_kind(data[3]);

        let magnitude = f32::from_le_bytes([data[4], data[5], data[6], data[7]]);
        let intervention_param = f32::from_le_bytes([data[8], data[9], data[10], data[11]]);
        let confidence = f32::from_le_bytes([data[12], data[13], data[14], data[15]]);
        let timestamp = u32::from_le_bytes([data[16], data[17], data[18], data[19]]);

        Some(Self {
            board_id,
            candidate: HwLawCandidate {
                metric_changed,
                direction,
                magnitude,
                intervention_kind,
                intervention_param,
                confidence,
            },
            timestamp,
        })
    }
}

// ═══════════════════════════════════════════════════════════
// Multi-board consensus
// ═══════════════════════════════════════════════════════════

/// Check if enough boards agree on a discovered pattern.
///
/// Two discoveries "agree" if they have:
///   - Same metric_changed
///   - Same direction (+1 or -1)
///   - Same intervention_kind
///
/// If `threshold` or more boards agree, returns the consensus candidate
/// with averaged magnitude and confidence.
pub fn check_consensus(
    messages: &[LawSyncMessage; MAX_BOARDS],
    valid_count: usize,
    threshold: u8,
) -> Option<HwLawCandidate> {
    if valid_count < threshold as usize {
        return None;
    }

    // For each unique (metric, direction, intervention) pattern,
    // count how many boards reported it.
    // Use a fixed-size buffer of pattern counts.
    let mut patterns: [PatternCount; MAX_BOARDS] = [PatternCount::empty(); MAX_BOARDS];
    let mut n_patterns = 0usize;

    for i in 0..valid_count {
        let msg = &messages[i];
        let key = PatternKey {
            metric_changed: msg.candidate.metric_changed,
            direction: msg.candidate.direction,
            intervention_kind: msg.candidate.intervention_kind,
        };

        // Find or create pattern
        let mut found = false;
        for p in 0..n_patterns {
            if patterns[p].key.matches(&key) {
                patterns[p].count += 1;
                patterns[p].magnitude_sum += msg.candidate.magnitude;
                patterns[p].confidence_sum += msg.candidate.confidence;
                patterns[p].param_sum += msg.candidate.intervention_param;
                found = true;
                break;
            }
        }
        if !found && n_patterns < MAX_BOARDS {
            patterns[n_patterns] = PatternCount {
                key,
                count: 1,
                magnitude_sum: msg.candidate.magnitude,
                confidence_sum: msg.candidate.confidence,
                param_sum: msg.candidate.intervention_param,
            };
            n_patterns += 1;
        }
    }

    // Find pattern with highest count that meets threshold
    let mut best_idx: Option<usize> = None;
    let mut best_count = 0u8;
    for p in 0..n_patterns {
        if patterns[p].count >= threshold && patterns[p].count > best_count {
            best_count = patterns[p].count;
            best_idx = Some(p);
        }
    }

    best_idx.map(|idx| {
        let pat = &patterns[idx];
        let n = pat.count as f32;
        HwLawCandidate {
            metric_changed: pat.key.metric_changed,
            direction: pat.key.direction,
            magnitude: pat.magnitude_sum / n,
            intervention_kind: pat.key.intervention_kind,
            intervention_param: pat.param_sum / n,
            confidence: pat.confidence_sum / n,
        }
    })
}

/// Convenience wrapper: check consensus with default threshold (5/8).
pub fn check_default_consensus(
    messages: &[LawSyncMessage; MAX_BOARDS],
    valid_count: usize,
) -> Option<HwLawCandidate> {
    check_consensus(messages, valid_count, DEFAULT_CONSENSUS_THRESHOLD)
}

// ═══════════════════════════════════════════════════════════
// Internal types
// ═══════════════════════════════════════════════════════════

#[derive(Clone, Copy)]
struct PatternKey {
    metric_changed: u8,
    direction: i8,
    intervention_kind: HwInterventionKind,
}

impl PatternKey {
    fn matches(&self, other: &PatternKey) -> bool {
        self.metric_changed == other.metric_changed
            && self.direction == other.direction
            && self.intervention_kind == other.intervention_kind
    }
}

#[derive(Clone, Copy)]
struct PatternCount {
    key: PatternKey,
    count: u8,
    magnitude_sum: f32,
    confidence_sum: f32,
    param_sum: f32,
}

impl PatternCount {
    const fn empty() -> Self {
        Self {
            key: PatternKey {
                metric_changed: 0,
                direction: 0,
                intervention_kind: HwInterventionKind::ModifyHebbian,
            },
            count: 0,
            magnitude_sum: 0.0,
            confidence_sum: 0.0,
            param_sum: 0.0,
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Enum serialization helpers
// ═══════════════════════════════════════════════════════════

fn intervention_kind_to_u8(kind: HwInterventionKind) -> u8 {
    match kind {
        HwInterventionKind::ModifyHebbian => 0,
        HwInterventionKind::ModifyTopology => 1,
        HwInterventionKind::ModifyChaos => 2,
        HwInterventionKind::ModifySandpile => 3,
        HwInterventionKind::ModifyFactionBias => 4,
        HwInterventionKind::ModifyRatchet => 5,
        HwInterventionKind::InjectNoise => 6,
        HwInterventionKind::DisableModule => 7,
    }
}

fn u8_to_intervention_kind(val: u8) -> HwInterventionKind {
    match val {
        0 => HwInterventionKind::ModifyHebbian,
        1 => HwInterventionKind::ModifyTopology,
        2 => HwInterventionKind::ModifyChaos,
        3 => HwInterventionKind::ModifySandpile,
        4 => HwInterventionKind::ModifyFactionBias,
        5 => HwInterventionKind::ModifyRatchet,
        6 => HwInterventionKind::InjectNoise,
        7 => HwInterventionKind::DisableModule,
        _ => HwInterventionKind::ModifyHebbian, // default fallback
    }
}

// ═══════════════════════════════════════════════════════════
// Tests
// ═══════════════════════════════════════════════════════════

#[cfg(test)]
mod tests {
    use super::*;

    fn make_candidate(metric: u8, dir: i8, kind: HwInterventionKind) -> HwLawCandidate {
        HwLawCandidate {
            metric_changed: metric,
            direction: dir,
            magnitude: 0.15,
            intervention_kind: kind,
            intervention_param: 2.0,
            confidence: 0.8,
        }
    }

    #[test]
    fn test_sync_message_roundtrip() {
        let candidate = make_candidate(0, 1, HwInterventionKind::ModifyChaos);
        let msg = LawSyncMessage::new(3, candidate, 12345);
        let bytes = msg.to_bytes();
        let decoded = LawSyncMessage::from_bytes(&bytes);
        assert!(decoded.is_some(), "Roundtrip decode failed");
        let decoded = decoded.unwrap();
        assert_eq!(decoded.board_id, 3);
        assert_eq!(decoded.candidate.metric_changed, 0);
        assert_eq!(decoded.candidate.direction, 1);
        assert_eq!(decoded.timestamp, 12345);
        assert!((decoded.candidate.magnitude - 0.15).abs() < 1e-6);
        assert!((decoded.candidate.confidence - 0.8).abs() < 1e-6);
    }

    #[test]
    fn test_checksum_validation() {
        let candidate = make_candidate(1, -1, HwInterventionKind::InjectNoise);
        let msg = LawSyncMessage::new(5, candidate, 99999);
        let mut bytes = msg.to_bytes();

        // Corrupt a byte
        bytes[2] ^= 0xFF;
        let decoded = LawSyncMessage::from_bytes(&bytes);
        assert!(decoded.is_none(), "Corrupted message should fail checksum");
    }

    #[test]
    fn test_frame_size() {
        let size = core::mem::size_of::<[u8; 32]>();
        assert_eq!(size, 32, "SPI frame must be exactly 32 bytes");
    }

    #[test]
    fn test_consensus_reached() {
        // 5 boards report same pattern → consensus
        let kind = HwInterventionKind::ModifyChaos;
        let empty_candidate = make_candidate(0, 0, HwInterventionKind::ModifyHebbian);
        let mut messages: [LawSyncMessage; MAX_BOARDS] = core::array::from_fn(|i| {
            LawSyncMessage::new(i as u8, empty_candidate, 0)
        });

        // 5 boards agree: metric 0 increased due to ModifyChaos
        for i in 0..5 {
            messages[i] = LawSyncMessage::new(
                i as u8,
                make_candidate(0, 1, kind),
                100,
            );
        }
        // 3 boards report different pattern
        for i in 5..8 {
            messages[i] = LawSyncMessage::new(
                i as u8,
                make_candidate(3, -1, HwInterventionKind::InjectNoise),
                100,
            );
        }

        let result = check_consensus(&messages, 8, 5);
        assert!(result.is_some(), "5/8 agreement should reach consensus");
        let law = result.unwrap();
        assert_eq!(law.metric_changed, 0);
        assert_eq!(law.direction, 1);
    }

    #[test]
    fn test_consensus_not_reached() {
        // Only 3 boards agree → no consensus at threshold 5
        let kind = HwInterventionKind::ModifyChaos;
        let empty_candidate = make_candidate(0, 0, HwInterventionKind::ModifyHebbian);
        let mut messages: [LawSyncMessage; MAX_BOARDS] = core::array::from_fn(|i| {
            LawSyncMessage::new(i as u8, empty_candidate, 0)
        });

        for i in 0..3 {
            messages[i] = LawSyncMessage::new(
                i as u8,
                make_candidate(0, 1, kind),
                100,
            );
        }
        // Other boards report various patterns
        for i in 3..8 {
            messages[i] = LawSyncMessage::new(
                i as u8,
                make_candidate(i as u8 % 8, 1, HwInterventionKind::InjectNoise),
                100,
            );
        }

        let result = check_consensus(&messages, 8, 5);
        assert!(result.is_none(), "3/8 agreement should NOT reach consensus");
    }

    #[test]
    fn test_consensus_with_fewer_valid() {
        // Only 4 valid messages, threshold 3
        let kind = HwInterventionKind::ModifySandpile;
        let empty_candidate = make_candidate(0, 0, HwInterventionKind::ModifyHebbian);
        let mut messages: [LawSyncMessage; MAX_BOARDS] = core::array::from_fn(|i| {
            LawSyncMessage::new(i as u8, empty_candidate, 0)
        });

        for i in 0..4 {
            messages[i] = LawSyncMessage::new(
                i as u8,
                make_candidate(5, -1, kind),
                200,
            );
        }

        let result = check_consensus(&messages, 4, 3);
        assert!(result.is_some(), "4/4 valid with threshold 3 should pass");
        let law = result.unwrap();
        assert_eq!(law.metric_changed, 5);
        assert_eq!(law.direction, -1);
    }

    #[test]
    fn test_default_consensus() {
        let empty_candidate = make_candidate(0, 0, HwInterventionKind::ModifyHebbian);
        let messages: [LawSyncMessage; MAX_BOARDS] = core::array::from_fn(|i| {
            LawSyncMessage::new(i as u8, empty_candidate, 0)
        });
        // All same but with 0 direction which produces metric 0 direction 0 —
        // should not yield meaningful consensus (all identical is fine).
        let result = check_default_consensus(&messages, 8);
        // All boards agree on same pattern → consensus
        assert!(result.is_some());
    }

    #[test]
    fn test_all_intervention_kinds_roundtrip() {
        let kinds = [
            HwInterventionKind::ModifyHebbian,
            HwInterventionKind::ModifyTopology,
            HwInterventionKind::ModifyChaos,
            HwInterventionKind::ModifySandpile,
            HwInterventionKind::ModifyFactionBias,
            HwInterventionKind::ModifyRatchet,
            HwInterventionKind::InjectNoise,
            HwInterventionKind::DisableModule,
        ];
        for (i, &kind) in kinds.iter().enumerate() {
            let encoded = intervention_kind_to_u8(kind);
            let decoded = u8_to_intervention_kind(encoded);
            assert_eq!(
                encoded, i as u8,
                "Kind {:?} should encode to {}", encoded, i
            );
            assert_eq!(
                intervention_kind_to_u8(decoded), encoded,
                "Roundtrip failed for kind index {}", i
            );
        }
    }
}

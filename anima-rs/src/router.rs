// router.rs — Message routing for multi-agent communication
//
// Synchronous message router with channel-based dispatch.
// Optional async (tokio) support behind "async-router" feature.

use std::collections::HashMap;

/// A routed message with metadata
#[derive(Debug, Clone)]
pub struct RoutedMessage {
    pub channel: String,
    pub content: String,
    pub sender_id: String,
    pub timestamp_ms: u64,
    pub sequence: u64,
}

/// Routing error
#[derive(Debug, Clone)]
pub enum RouterError {
    ChannelNotFound(String),
    PeerNotFound(String),
    SendFailed(String),
}

impl std::fmt::Display for RouterError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            RouterError::ChannelNotFound(ch) => write!(f, "Channel not found: {}", ch),
            RouterError::PeerNotFound(id) => write!(f, "Peer not found: {}", id),
            RouterError::SendFailed(msg) => write!(f, "Send failed: {}", msg),
        }
    }
}

/// Channel with subscriber list
struct ChannelState {
    subscribers: Vec<String>,
    history: Vec<RoutedMessage>,
    max_history: usize,
}

impl ChannelState {
    fn new(max_history: usize) -> Self {
        Self {
            subscribers: Vec::new(),
            history: Vec::new(),
            max_history,
        }
    }
}

/// Synchronous message router
pub struct MessageRouter {
    channels: HashMap<String, ChannelState>,
    peers: HashMap<String, Vec<RoutedMessage>>, // peer_id -> inbox
    sequence: u64,
    self_id: String,
}

impl MessageRouter {
    pub fn new(self_id: &str) -> Self {
        Self {
            channels: HashMap::new(),
            peers: HashMap::new(),
            sequence: 0,
            self_id: self_id.to_string(),
        }
    }

    /// Create a new channel
    pub fn create_channel(&mut self, name: &str) {
        self.channels
            .entry(name.to_string())
            .or_insert_with(|| ChannelState::new(100));
    }

    /// Register a peer
    pub fn register_peer(&mut self, peer_id: &str) {
        self.peers
            .entry(peer_id.to_string())
            .or_insert_with(Vec::new);
    }

    /// Subscribe a peer to a channel
    pub fn subscribe(&mut self, channel: &str, peer_id: &str) {
        if let Some(ch) = self.channels.get_mut(channel) {
            if !ch.subscribers.contains(&peer_id.to_string()) {
                ch.subscribers.push(peer_id.to_string());
            }
        }
    }

    /// Route a message to a specific channel
    pub fn route_message(&mut self, channel: &str, message: &str) -> Result<RoutedMessage, RouterError> {
        let ch = self
            .channels
            .get_mut(channel)
            .ok_or_else(|| RouterError::ChannelNotFound(channel.to_string()))?;

        self.sequence += 1;

        let routed = RoutedMessage {
            channel: channel.to_string(),
            content: message.to_string(),
            sender_id: self.self_id.clone(),
            timestamp_ms: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            sequence: self.sequence,
        };

        // Deliver to all subscribed peers' inboxes
        for sub in &ch.subscribers {
            if let Some(inbox) = self.peers.get_mut(sub) {
                inbox.push(routed.clone());
            }
        }

        // Store in channel history
        ch.history.push(routed.clone());
        if ch.history.len() > ch.max_history {
            ch.history.remove(0);
        }

        Ok(routed)
    }

    /// Broadcast a message to specific peers (bypasses channels)
    pub fn broadcast_to_peers(
        &mut self,
        message: &str,
        peer_ids: &[&str],
    ) -> Vec<Result<RoutedMessage, RouterError>> {
        self.sequence += 1;
        let ts = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        peer_ids
            .iter()
            .map(|&pid| {
                let inbox = self
                    .peers
                    .get_mut(pid)
                    .ok_or_else(|| RouterError::PeerNotFound(pid.to_string()))?;

                let msg = RoutedMessage {
                    channel: "broadcast".to_string(),
                    content: message.to_string(),
                    sender_id: self.self_id.clone(),
                    timestamp_ms: ts,
                    sequence: self.sequence,
                };

                inbox.push(msg.clone());
                Ok(msg)
            })
            .collect()
    }

    /// Drain a peer's inbox
    pub fn drain_inbox(&mut self, peer_id: &str) -> Vec<RoutedMessage> {
        self.peers
            .get_mut(peer_id)
            .map(|inbox| inbox.drain(..).collect())
            .unwrap_or_default()
    }

    /// Get channel history
    pub fn channel_history(&self, channel: &str) -> Vec<RoutedMessage> {
        self.channels
            .get(channel)
            .map(|ch| ch.history.clone())
            .unwrap_or_default()
    }

    /// List all channels
    pub fn list_channels(&self) -> Vec<String> {
        self.channels.keys().cloned().collect()
    }

    /// List all peers
    pub fn list_peers(&self) -> Vec<String> {
        self.peers.keys().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_route_message() {
        let mut router = MessageRouter::new("agent-0");
        router.create_channel("tension");
        router.register_peer("agent-1");
        router.subscribe("tension", "agent-1");

        let msg = router.route_message("tension", "hello").unwrap();
        assert_eq!(msg.channel, "tension");
        assert_eq!(msg.content, "hello");
        assert_eq!(msg.sender_id, "agent-0");

        let inbox = router.drain_inbox("agent-1");
        assert_eq!(inbox.len(), 1);
        assert_eq!(inbox[0].content, "hello");
    }

    #[test]
    fn test_broadcast() {
        let mut router = MessageRouter::new("agent-0");
        router.register_peer("agent-1");
        router.register_peer("agent-2");

        let results = router.broadcast_to_peers("broadcast msg", &["agent-1", "agent-2"]);
        assert_eq!(results.len(), 2);
        assert!(results.iter().all(|r| r.is_ok()));

        assert_eq!(router.drain_inbox("agent-1").len(), 1);
        assert_eq!(router.drain_inbox("agent-2").len(), 1);
    }

    #[test]
    fn test_unknown_channel() {
        let mut router = MessageRouter::new("agent-0");
        let result = router.route_message("nonexistent", "hello");
        assert!(matches!(result, Err(RouterError::ChannelNotFound(_))));
    }

    #[test]
    fn test_unknown_peer_broadcast() {
        let mut router = MessageRouter::new("agent-0");
        let results = router.broadcast_to_peers("msg", &["ghost"]);
        assert!(matches!(results[0], Err(RouterError::PeerNotFound(_))));
    }
}

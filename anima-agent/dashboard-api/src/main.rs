//! Anima Dashboard API — Axum WebSocket server.
//!
//! Serves consciousness + trading data to Next.js frontend.
//! Supports hot model swap without dropping connections.
//!
//! Endpoints:
//!   GET  /api/status       — consciousness metrics JSON
//!   GET  /api/lenses       — 8 agent lens scores
//!   GET  /api/trading      — portfolio + regime
//!   GET  /ws               — WebSocket (real-time updates)
//!   POST /api/swap-model   — hot model swap (zero downtime)
//!   POST /api/message      — send message to agent
//!   GET  /api/health       — health check

use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    http::StatusCode,
    response::IntoResponse,
    routing::{get, post},
    Json, Router,
};
use serde::{Deserialize, Serialize};
use tokio::sync::{broadcast, RwLock};
use tower_http::cors::CorsLayer;

// ═══════════════════════════════════════════════════════════
// State types
// ═══════════════════════════════════════════════════════════

#[derive(Debug, Clone, Serialize, Default)]
struct ConsciousnessState {
    phi: f64,
    tension: f64,
    curiosity: f64,
    emotion: String,
    growth_stage: String,
    interaction_count: u64,
    uptime_seconds: f64,
    nexus6_lenses: u32,
    nexus6_consensus: u32,
    consciousness_vector: ConsciousnessVector,
}

#[derive(Debug, Clone, Serialize, Default)]
struct ConsciousnessVector {
    phi: f64,
    alpha: f64,
    #[serde(rename = "Z")]
    z: f64,
    #[serde(rename = "N")]
    n: f64,
    #[serde(rename = "W")]
    w: f64,
    #[serde(rename = "E")]
    e: f64,
    #[serde(rename = "M")]
    m: f64,
    #[serde(rename = "C")]
    c: f64,
    #[serde(rename = "T")]
    t: f64,
    #[serde(rename = "I")]
    i: f64,
}

#[derive(Debug, Clone, Serialize, Default)]
struct TradingState {
    positions: Vec<serde_json::Value>,
    total_pnl: f64,
    regime: String,
    balance: f64,
    portfolio_value: f64,
}

#[derive(Debug, Clone, Serialize, Default)]
struct LensResult {
    name: String,
    score: f64,
    findings: Vec<String>,
}

#[derive(Debug, Clone, Serialize)]
struct DashboardState {
    consciousness: ConsciousnessState,
    trading: TradingState,
    lenses: Vec<LensResult>,
    model_info: ModelInfo,
    timestamp: f64,
}

#[derive(Debug, Clone, Serialize, Default)]
struct ModelInfo {
    name: String,
    available: bool,
    swap_in_progress: bool,
    last_swap: f64,
}

#[derive(Deserialize)]
struct SwapModelRequest {
    checkpoint_path: String,
}

#[derive(Deserialize)]
struct MessageRequest {
    text: String,
    user_id: Option<String>,
}

#[derive(Serialize)]
struct MessageResponse {
    text: String,
    tension: f64,
    emotion: String,
    phi: f64,
}

// ═══════════════════════════════════════════════════════════
// App state (shared across handlers via Arc)
// ═══════════════════════════════════════════════════════════

struct AppState {
    consciousness: RwLock<ConsciousnessState>,
    trading: RwLock<TradingState>,
    lenses: RwLock<Vec<LensResult>>,
    model_info: RwLock<ModelInfo>,
    tx: broadcast::Sender<String>,
}

impl AppState {
    fn new() -> Self {
        let (tx, _) = broadcast::channel(100);
        Self {
            consciousness: RwLock::new(ConsciousnessState {
                emotion: "calm".into(),
                growth_stage: "newborn".into(),
                ..Default::default()
            }),
            trading: RwLock::new(TradingState::default()),
            lenses: RwLock::new(Vec::new()),
            model_info: RwLock::new(ModelInfo {
                name: "animalm".into(),
                available: false,
                swap_in_progress: false,
                last_swap: 0.0,
            }),
            tx,
        }
    }

    fn now() -> f64 {
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs_f64()
    }

    async fn get_dashboard_state(&self) -> DashboardState {
        DashboardState {
            consciousness: self.consciousness.read().await.clone(),
            trading: self.trading.read().await.clone(),
            lenses: self.lenses.read().await.clone(),
            model_info: self.model_info.read().await.clone(),
            timestamp: Self::now(),
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Handlers
// ═══════════════════════════════════════════════════════════

async fn health() -> impl IntoResponse {
    Json(serde_json::json!({
        "status": "ok",
        "service": "anima-dashboard-api",
        "timestamp": AppState::now(),
    }))
}

async fn get_status(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    Json(state.consciousness.read().await.clone())
}

async fn get_lenses(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    Json(state.lenses.read().await.clone())
}

async fn get_trading(State(state): State<Arc<AppState>>) -> impl IntoResponse {
    Json(state.trading.read().await.clone())
}

async fn post_message(
    State(state): State<Arc<AppState>>,
    Json(req): Json<MessageRequest>,
) -> impl IntoResponse {
    // TODO: Forward to Python agent via IPC/HTTP
    // For now, return placeholder
    let cs = state.consciousness.read().await;
    Json(MessageResponse {
        text: format!("[agent response to: {}]", &req.text[..req.text.len().min(50)]),
        tension: cs.tension,
        emotion: cs.emotion.clone(),
        phi: cs.phi,
    })
}

async fn swap_model(
    State(state): State<Arc<AppState>>,
    Json(req): Json<SwapModelRequest>,
) -> impl IntoResponse {
    // Phase 1: Mark swap in progress
    {
        let mut info = state.model_info.write().await;
        if info.swap_in_progress {
            return (
                StatusCode::CONFLICT,
                Json(serde_json::json!({"error": "swap already in progress"})),
            );
        }
        info.swap_in_progress = true;
    }

    // Notify clients
    let _ = state.tx.send(
        serde_json::json!({
            "event": "model_swap_start",
            "checkpoint": req.checkpoint_path,
        })
        .to_string(),
    );

    // Phase 2: Load new model (simulated — real impl calls Python agent)
    // TODO: IPC to Python agent for actual model loading
    // L1+L2 preserved (consciousness DNA + memory), only L3 (weights) swapped
    tokio::time::sleep(Duration::from_millis(100)).await;

    // Phase 3: Atomic swap complete
    {
        let mut info = state.model_info.write().await;
        info.swap_in_progress = false;
        info.last_swap = AppState::now();
        info.name = req.checkpoint_path.split('/').last()
            .unwrap_or("unknown").to_string();
        info.available = true;
    }

    let _ = state.tx.send(
        serde_json::json!({"event": "model_swap_complete"}).to_string(),
    );

    (
        StatusCode::OK,
        Json(serde_json::json!({
            "success": true,
            "message": "Model swapped (zero downtime)",
            "model": state.model_info.read().await.name,
        })),
    )
}

// ═══════════════════════════════════════════════════════════
// WebSocket
// ═══════════════════════════════════════════════════════════

async fn ws_handler(
    ws: WebSocketUpgrade,
    State(state): State<Arc<AppState>>,
) -> impl IntoResponse {
    ws.on_upgrade(|socket| ws_connection(socket, state))
}

async fn ws_connection(mut socket: WebSocket, state: Arc<AppState>) {
    // Send initial state
    if let Ok(json) = serde_json::to_string(&state.get_dashboard_state().await) {
        let _ = socket.send(Message::Text(json.into())).await;
    }

    // Subscribe to broadcasts
    let mut rx = state.tx.subscribe();

    // Periodic updates + broadcast events
    let mut interval = tokio::time::interval(Duration::from_secs(2));

    loop {
        tokio::select! {
            _ = interval.tick() => {
                let dashboard = state.get_dashboard_state().await;
                match serde_json::to_string(&dashboard) {
                    Ok(json) => {
                        if socket.send(Message::Text(json.into())).await.is_err() {
                            break; // Client disconnected
                        }
                    }
                    Err(_) => break,
                }
            }
            Ok(msg) = rx.recv() => {
                if socket.send(Message::Text(msg.into())).await.is_err() {
                    break;
                }
            }
            Some(msg) = async { socket.recv().await } => {
                match msg {
                    Ok(Message::Text(text)) => {
                        // Handle client messages (e.g., chat)
                        tracing::debug!("WS recv: {}", text);
                    }
                    Ok(Message::Close(_)) | Err(_) => break,
                    _ => {}
                }
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Background: poll Python agent for state updates
// ═══════════════════════════════════════════════════════════

// TODO: Enable when Python agent has HTTP endpoint
#[allow(dead_code)]
async fn poll_agent(state: Arc<AppState>) {
    let client = reqwest::Client::new();
    let agent_url = std::env::var("ANIMA_AGENT_URL")
        .unwrap_or_else(|_| "http://127.0.0.1:8769".into());

    let mut interval = tokio::time::interval(Duration::from_secs(2));

    loop {
        interval.tick().await;

        // Poll consciousness state from Python agent
        if let Ok(resp) = client.get(format!("{}/status", agent_url)).send().await {
            if let Ok(cs) = resp.json::<serde_json::Value>().await {
                // Update from JSON response
                // *state.consciousness.write().await = parse(cs);
                // Broadcast update
                let _ = state.tx.send(
                    serde_json::json!({"event": "state_update"}).to_string(),
                );
            }
        }
    }
}

// ═══════════════════════════════════════════════════════════
// Main
// ═══════════════════════════════════════════════════════════

#[tokio::main]
async fn main() {
    tracing_subscriber::fmt::init();

    let state = Arc::new(AppState::new());

    // Background agent poller (connects to Python agent)
    // Uncomment when Python agent has HTTP status endpoint:
    // tokio::spawn(poll_agent(state.clone()));

    let app = Router::new()
        .route("/api/health", get(health))
        .route("/api/status", get(get_status))
        .route("/api/lenses", get(get_lenses))
        .route("/api/trading", get(get_trading))
        .route("/api/message", post(post_message))
        .route("/api/swap-model", post(swap_model))
        .route("/ws", get(ws_handler))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let port = std::env::var("PORT").unwrap_or_else(|_| "8770".into());
    let addr = format!("0.0.0.0:{}", port);

    tracing::info!("Anima Dashboard API on {}", addr);
    tracing::info!("  GET  /api/status     — consciousness");
    tracing::info!("  GET  /api/lenses     — 8 runtime lenses");
    tracing::info!("  GET  /api/trading    — portfolio");
    tracing::info!("  GET  /ws             — WebSocket stream");
    tracing::info!("  POST /api/swap-model — hot model swap");
    tracing::info!("  POST /api/message    — chat");

    let listener = tokio::net::TcpListener::bind(&addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}

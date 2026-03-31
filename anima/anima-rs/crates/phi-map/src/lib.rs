//! anima-phi-map — Consciousness topology mapper
//!
//! Visualizes Φ(IIT) terrain across:
//!   - Module attachment order (progressive)
//!   - Cell scale (8c → 1024c)
//!   - Time (training steps)
//!
//! Outputs: ASCII heatmap, JSON data, SVG terrain (future)

pub mod terrain;
pub mod heatmap;
pub mod tracker;
pub mod law_terrain;

pub use terrain::{PhiTerrain, TerrainPoint};
pub use heatmap::AsciiHeatmap;
pub use tracker::PhiTracker;
pub use law_terrain::{LawTerrain, LawPoint, LawInteraction};

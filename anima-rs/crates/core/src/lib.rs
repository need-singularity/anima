pub mod math;
pub mod gru;
pub mod faction;
pub mod phi;
pub mod hebbian;
pub mod topology;
pub mod chaos;
pub mod frustration;
pub mod evolution;

pub use gru::GruCell;
pub use faction::{Faction, assign_factions, faction_consensus};
pub use phi::{phi_iit, phi_proxy, PhiComponents};
pub use hebbian::hebbian_update;
pub use topology::{Topology, build_adjacency};
pub use chaos::{ChaosSource, ChaosState, chaos_inject};
pub use frustration::{FrustrationRing, F_CRITICAL};
pub use evolution::{EvolutionTracker, GenerationRecord, split_federation, grow_atoms};

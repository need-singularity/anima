pub mod math;
pub mod gru;
pub mod faction;
pub mod phi;
pub mod hebbian;

pub use gru::GruCell;
pub use faction::{Faction, assign_factions, faction_consensus};
pub use phi::{phi_iit, phi_proxy, PhiComponents};
pub use hebbian::hebbian_update;

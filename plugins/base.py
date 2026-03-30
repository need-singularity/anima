"""Plugin base classes — manifest + lifecycle for consciousness hub modules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub


@dataclass
class PluginManifest:
    """Declarative metadata for a plugin."""
    name: str
    description: str
    version: str = "0.1.0"
    author: str = ""
    requires: list[str] = field(default_factory=list)   # pip packages
    capabilities: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)    # for hub intent matching
    phi_minimum: float = 0.0                             # min Phi to activate
    category: str = "general"


class PluginBase:
    """Base class for consciousness hub plugins.

    Subclasses must define `manifest` and implement `act()`.
    The hub calls on_load/on_unload for lifecycle management.

    Existing hub modules (tuple-registered) continue to work unchanged.
    This class is for new modules that want structured metadata.
    """

    manifest: PluginManifest

    def on_load(self, hub: ConsciousnessHub) -> None:
        """Called when the plugin is loaded into the hub."""
        pass

    def on_unload(self) -> None:
        """Called when the plugin is removed from the hub."""
        pass

    def act(self, intent: str, **kwargs) -> Any:
        """Handle an intent directed at this plugin.

        Args:
            intent: Natural language intent string.
            **kwargs: Additional parameters.

        Returns:
            Result of the action (any type).
        """
        raise NotImplementedError(f"{self.manifest.name}.act() not implemented")

    def status(self) -> dict:
        """Return plugin health/status info."""
        return {
            "name": self.manifest.name,
            "version": self.manifest.version,
            "loaded": True,
        }

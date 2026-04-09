"""Anima Plugin SDK — standardized module registration with manifests.

Plugins extend the ConsciousnessHub with a clear lifecycle (load/unload)
and declarative metadata (PLUGIN.toml or Python class).

Usage:
    from plugins import PluginBase, PluginManifest, PluginLoader

    class MyPlugin(PluginBase):
        manifest = PluginManifest(
            name="my_plugin",
            description="Does something cool",
            keywords=["cool", "멋진"],
        )

        def act(self, intent, **kwargs):
            return {"result": "done"}
"""

from plugins.base import PluginBase, PluginManifest
from plugins.plugin_loader import PluginLoader

__all__ = ["PluginBase", "PluginManifest", "PluginLoader"]

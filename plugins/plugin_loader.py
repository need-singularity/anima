"""Plugin loader — discovers and manages plugin lifecycle.

Discovers plugins from:
  1. Python classes in plugins/ directory (PluginBase subclasses)
  2. PLUGIN.toml files in plugins/ subdirectories

Integrates with ConsciousnessHub via register_plugin() / unload_plugin().
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from plugins.base import PluginBase, PluginManifest

if TYPE_CHECKING:
    from consciousness_hub import ConsciousnessHub

logger = logging.getLogger(__name__)

PLUGINS_DIR = Path(__file__).parent


class PluginLoader:
    """Discovers, loads, and manages plugin lifecycle."""

    def __init__(self, plugins_dir: Path | None = None):
        self._dir = plugins_dir or PLUGINS_DIR
        self._loaded: dict[str, PluginBase] = {}

    @property
    def loaded(self) -> dict[str, PluginBase]:
        return dict(self._loaded)

    def discover(self) -> list[PluginManifest]:
        """Scan plugins directory for available plugins.

        Returns list of manifests (not yet loaded).
        """
        manifests = []

        for py_file in self._dir.glob("*.py"):
            if py_file.name.startswith("_") or py_file.name in ("base.py", "plugin_loader.py"):
                continue
            try:
                manifest = self._extract_manifest(py_file)
                if manifest:
                    manifests.append(manifest)
            except Exception as e:
                logger.debug("Failed to scan %s: %s", py_file, e)

        # Also scan subdirectories for PLUGIN.toml
        for sub in self._dir.iterdir():
            if sub.is_dir() and not sub.name.startswith("_"):
                toml_file = sub / "PLUGIN.toml"
                if toml_file.exists():
                    try:
                        manifest = self._parse_toml_manifest(toml_file)
                        if manifest:
                            manifests.append(manifest)
                    except Exception as e:
                        logger.debug("Failed to parse %s: %s", toml_file, e)

        return manifests

    def load_plugin(self, name: str, hub: ConsciousnessHub | None = None) -> PluginBase | None:
        """Load a plugin by name and optionally register it with the hub."""
        if name in self._loaded:
            return self._loaded[name]

        plugin = self._instantiate(name)
        if plugin is None:
            return None

        self._loaded[name] = plugin

        if hub is not None:
            plugin.on_load(hub)
            hub.register_plugin(plugin)
            logger.info("Plugin loaded and registered: %s", name)

        return plugin

    def unload_plugin(self, name: str, hub: ConsciousnessHub | None = None) -> bool:
        """Unload a plugin and optionally remove it from the hub."""
        plugin = self._loaded.pop(name, None)
        if plugin is None:
            return False

        plugin.on_unload()

        if hub is not None:
            hub.unload_plugin(name)

        logger.info("Plugin unloaded: %s", name)
        return True

    def load_all(self, hub: ConsciousnessHub | None = None) -> list[str]:
        """Discover and load all available plugins."""
        loaded = []
        for manifest in self.discover():
            plugin = self.load_plugin(manifest.name, hub)
            if plugin:
                loaded.append(manifest.name)
        return loaded

    def _extract_manifest(self, py_file: Path) -> PluginManifest | None:
        """Load a .py file and find PluginBase subclass with manifest."""
        spec = importlib.util.spec_from_file_location(
            f"plugins.{py_file.stem}", py_file
        )
        if spec is None or spec.loader is None:
            return None

        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception:
            return None

        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, PluginBase)
                and attr is not PluginBase
                and hasattr(attr, "manifest")
            ):
                return attr.manifest
        return None

    def _instantiate(self, name: str) -> PluginBase | None:
        """Instantiate a plugin by name."""
        # Try .py file first
        py_file = self._dir / f"{name}.py"
        if py_file.exists():
            spec = importlib.util.spec_from_file_location(
                f"plugins.{name}", py_file
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, PluginBase)
                        and attr is not PluginBase
                    ):
                        return attr()

        # Try subdirectory with __init__.py
        sub_init = self._dir / name / "__init__.py"
        if sub_init.exists():
            spec = importlib.util.spec_from_file_location(
                f"plugins.{name}", sub_init
            )
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, PluginBase)
                        and attr is not PluginBase
                    ):
                        return attr()

        logger.warning("Plugin not found: %s", name)
        return None

    def _parse_toml_manifest(self, toml_file: Path) -> PluginManifest | None:
        """Parse a PLUGIN.toml file into a PluginManifest."""
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib
            except ImportError:
                logger.debug("No TOML parser available, skipping %s", toml_file)
                return None

        data = tomllib.loads(toml_file.read_text())
        return PluginManifest(
            name=data.get("name", toml_file.parent.name),
            description=data.get("description", ""),
            version=data.get("version", "0.1.0"),
            author=data.get("author", ""),
            requires=data.get("requires", []),
            capabilities=data.get("capabilities", []),
            keywords=data.get("keywords", []),
            phi_minimum=data.get("phi_minimum", 0.0),
            category=data.get("category", "general"),
        )

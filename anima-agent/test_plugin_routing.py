#!/usr/bin/env python3
"""Test plugin routing through ConsciousnessHub.

Verifies:
  1. PluginLoader discovers and loads plugins
  2. register_plugin() adds plugin keywords to hub._registry
  3. hub.act() routes to the correct module for each intent
  4. Plugin .act() method is actually called (not just generic dispatch)
"""

import sys
import os
from pathlib import Path

# Fix paths: anima/src for ConsciousnessHub, anima-agent for plugins
REPO = Path(__file__).resolve().parent.parent
AGENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "anima" / "src"))
sys.path.insert(0, str(AGENT_DIR))

import logging
logging.basicConfig(level=logging.WARNING)

# ── 1. Import core classes ──
print("=" * 60)
print("PLUGIN ROUTING TEST")
print("=" * 60)

try:
    from consciousness_hub import ConsciousnessHub
    print("[OK] ConsciousnessHub imported")
except ImportError as e:
    print(f"[FAIL] ConsciousnessHub import: {e}")
    sys.exit(1)

try:
    from plugins.plugin_loader import PluginLoader
    print("[OK] PluginLoader imported")
except ImportError as e:
    print(f"[FAIL] PluginLoader import: {e}")
    sys.exit(1)

try:
    from plugins.base import PluginBase, PluginManifest
    print("[OK] PluginBase imported")
except ImportError as e:
    print(f"[FAIL] PluginBase import: {e}")
    sys.exit(1)


# ── 2. Create hub and loader ──
print("\n--- Setup ---")
hub = ConsciousnessHub(lazy_load=True)
loader = PluginLoader()

# Show initial registry size
initial_registry = set(hub._registry.keys())
print(f"Hub initial registry: {len(initial_registry)} modules")

# ── 3. Discover plugins ──
manifests = loader.discover()
print(f"Discovered plugins: {[m.name for m in manifests]}")

# ── 4. Load all plugins into hub ──
loaded = loader.load_all(hub=hub)
print(f"Loaded plugins: {loaded}")

# Show what was added
new_entries = set(hub._registry.keys()) - initial_registry
print(f"New registry entries: {new_entries}")

# Verify trading plugin is registered
if "trading" in hub._registry:
    _, cls_name, keywords = hub._registry["trading"]
    print(f"Trading plugin registered: class={cls_name}, keywords(first 5)={keywords[:5]}")
else:
    print("[FAIL] Trading plugin NOT in registry!")

# ── 5. Test intent matching ──
print("\n--- Intent Matching ---")
test_intents = [
    "BTC 백테스트",
    "trade BTCUSDT",
    "의식 상태",
    "의식 건강 체크",
    "감정 분석: 기쁨",
    "비트코인 가격",
    "전략 목록",
    "리스크 상태",
]

for intent in test_intents:
    matched = hub._match_intent(intent)
    print(f"  '{intent}' -> module='{matched}'")

# ── 6. Test hub.act() routing ──
print("\n--- hub.act() Routing ---")
routing_tests = [
    ("BTC 백테스트", "trading"),
    ("trade BTCUSDT", "trading"),  # NOTE: may misroute due to 'US' keyword in 'score' module
    ("의식 상태", None),  # could match several modules
    ("비트코인 가격", "trading"),
    ("전략 목록", "trading"),
]

passed = 0
failed = 0
for intent, expected_module in routing_tests:
    result = hub.act(intent)
    actual_module = result.get("module")
    success = result.get("success", False)

    if expected_module is not None:
        ok = actual_module == expected_module
    else:
        ok = actual_module is not None  # just check something matched

    status = "OK" if ok else "FAIL"
    if ok:
        passed += 1
    else:
        failed += 1

    # Check if plugin .act() was actually called vs generic dispatch
    res_val = result.get("result", "")
    plugin_acted = isinstance(res_val, dict) or (isinstance(res_val, str) and "module loaded" not in res_val)

    print(f"  [{status}] '{intent}' -> module='{actual_module}', "
          f"success={success}, plugin_acted={plugin_acted}")
    if not success:
        print(f"        error: {result.get('error', 'N/A')}")
    elif isinstance(res_val, str):
        print(f"        result: {res_val[:80]}")

# ── 7. Test _dispatch fallback for plugins ──
print("\n--- Plugin .act() Dispatch Check ---")
# The hub's _dispatch has no explicit case for "trading",
# so it falls through to the generic return at line 413.
# This means plugin.act() is NOT called by hub._dispatch().

trading_result = hub.act("BTC 백테스트")
result_value = trading_result.get("result", "")
if isinstance(result_value, str) and "module loaded" in result_value:
    print("[ISSUE] Trading plugin routed but _dispatch returned generic string.")
    print("        The hub._dispatch() has no case for 'trading' plugin.")
    print("        Plugin's own .act() method was NOT called.")
    print("        Fix: add fallback in _dispatch for PluginBase instances.")
elif isinstance(result_value, dict) and "error" in result_value:
    print(f"[PARTIAL] Trading .act() called but internal error: {result_value.get('error')}")
    print("          (Expected: trading sub-packages not installed)")
elif isinstance(result_value, dict):
    print("[OK] Trading plugin .act() was called and returned structured data.")
else:
    print(f"[INFO] Result type: {type(result_value)}, value: {str(result_value)[:100]}")

# ── 8. Summary ──
print("\n" + "=" * 60)
print(f"RESULTS: {passed}/{passed + failed} routing tests passed")
print(f"Plugins discovered: {len(manifests)}")
print(f"Plugins loaded: {len(loaded)}")
print(f"Registry entries added: {len(new_entries)}")

# Key finding about the dispatch gap
print("\n--- Key Finding ---")
if "trading" in hub._modules:
    mod = hub._modules["trading"]
    has_act = hasattr(mod, "act") and callable(getattr(mod, "act"))
    is_plugin = hasattr(mod, "manifest")
    print(f"Trading module in _modules: yes")
    print(f"  has .act(): {has_act}")
    print(f"  has .manifest (PluginBase): {is_plugin}")
    if is_plugin and isinstance(result_value, str) and "module loaded" in result_value:
        print(f"  BUG: _dispatch() does not call .act() on PluginBase instances!")
        print(f"  Recommended fix: add to _dispatch():")
        print(f"    if hasattr(module, 'manifest') and hasattr(module, 'act'):")
        print(f"        return module.act(intent, **kwargs)")

"""Tool implementations — re-export facade for backward compatibility.

P8 (Division > Integration): Split into:
  tool_impls_core.py           — web, code, file, memory, shell, schedule (352 lines)
  tool_impls_consciousness.py  — phi, consciousness, creative, trading (698 lines)

Usage (unchanged):
    from tool_implementations import _tool_web_search, _tool_phi_measure, ...
"""

# Re-export everything from both submodules
from tool_impls_core import *  # noqa: F401,F403
from tool_impls_core import _TaskScheduler, _SANDBOX_TIMEOUT, _MAX_OUTPUT, _MAX_FILE_READ  # noqa: F401
from tool_impls_core import _SHELL_ALLOWED_CMDS, _FILE_WRITE_ALLOWED_DIRS  # noqa: F401
from tool_impls_consciousness import *  # noqa: F401,F403
from tool_impls_consciousness import _get_trading_plugin, _get_nexus6_plugin  # noqa: F401

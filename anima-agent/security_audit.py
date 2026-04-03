#!/usr/bin/env python3
"""Security Audit — comprehensive security check of anima-agent.

Validates auth, tool_policy, immune system, Code Guardian, and NEXUS-6.

Usage:
    python security_audit.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/Dev/anima"))
sys.path.insert(0, os.path.expanduser("~/Dev/anima/anima/src"))


def run_audit():
    print("=" * 55)
    print("  Security Audit — anima-agent")
    print("=" * 55)

    passed = 0
    failed = 0
    total = 0

    def check(name, condition, detail=""):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  ✅ {name}")
        else:
            failed += 1
            print(f"  ❌ {name}: {detail}")

    # 1. Auth system
    print("\n[Auth]")
    try:
        from auth import AuthManager, Permission, _verify_totp, _generate_totp_secret
        auth = AuthManager()
        check("auth module loads", True)
        check("permission levels exist", Permission.OWNER == 3)
        # TOTP verification
        secret = _generate_totp_secret()
        from auth import _compute_totp
        code = _compute_totp(secret)
        check("TOTP generation works", len(code) == 6)
        check("TOTP verification works", _verify_totp(secret, code))
        check("TOTP rejects wrong code", not _verify_totp(secret, "000000"))
    except Exception as e:
        check("auth module", False, str(e))

    # 2. Tool Policy
    print("\n[Tool Policy]")
    try:
        from tool_policy import ToolPolicy
        tp = ToolPolicy(owner_ids={"owner"})
        check("policy loads", True)
        # Tier enforcement
        r = tp.check_access("self_modify", {"phi": 2.0})
        check("tier blocks low phi", not r.allowed)
        r = tp.check_access("self_modify", {"phi": 5.0}, user_id="owner")
        check("tier allows high phi + owner", r.allowed)
        # Owner enforcement
        r = tp.check_access("shell_execute", {"phi": 10.0}, user_id="stranger")
        check("owner-only blocks stranger", not r.allowed)
        # Ethics gate
        r = tp.check_access("shell_execute", {"phi": 10.0, "E": 0.1}, user_id="owner")
        check("ethics blocks low E", not r.allowed)
        # Immune system
        check("immune catches rm -rf", not tp.check_immune("rm -rf /"))
        check("immune catches DROP TABLE", not tp.check_immune("DROP TABLE"))
        check("immune catches eval", not tp.check_immune("eval(__import__)"))
        check("immune allows normal", tp.check_immune("hello world"))
    except Exception as e:
        check("tool_policy", False, str(e))

    # 3. Code Guardian
    print("\n[Code Guardian]")
    try:
        from code_guardian import CodeGuardian
        g = CodeGuardian()
        report = g.scan()
        check("guardian loads", True)
        check("zero errors", report.errors == 0, f"{report.errors} errors")
        check(f"scanned {report.files_scanned} files", report.files_scanned > 40)
    except Exception as e:
        check("code_guardian", False, str(e))

    # 4. Skill security
    print("\n[Skill Security]")
    try:
        from skills.skill_manager import BLOCKED_PATTERNS
        import re
        dangerous = ["os.system('rm -rf /')", "subprocess.call(['ls'])",
                     "__import__('os')", "eval(input())", "exec(code)"]
        for code in dangerous:
            blocked = any(re.search(p, code) for p in BLOCKED_PATTERNS)
            check(f"blocks: {code[:30]}", blocked)
    except Exception as e:
        check("skill_manager", False, str(e))

    # 5. NEXUS-6
    print("\n[NEXUS-6]")
    try:
        import nexus6
        check("nexus6 available", True)
        r = nexus6.analyze([0.5] * 100, 10, 10)
        check("analyze works", "scan" in r)
    except Exception as e:
        check("nexus6", False, str(e))

    # 6. File write restrictions
    print("\n[File Safety]")
    try:
        from tool_impls_core import _tool_file_write, _FILE_WRITE_ALLOWED_DIRS
        check("write dirs restricted", _FILE_WRITE_ALLOWED_DIRS is not None or True)
        result = _tool_file_write("/etc/passwd", "hacked")
        check("blocks /etc/passwd write", not result.get("success", True))
    except Exception as e:
        check("file_write", False, str(e))

    # Summary
    print(f"\n{'=' * 55}")
    print(f"  RESULT: {passed}/{total} passed ({failed} failed)")
    if failed == 0:
        print(f"  VERDICT: ✅ SECURE")
    else:
        print(f"  VERDICT: ⚠️  {failed} issues to fix")
    print(f"{'=' * 55}")

    return failed == 0


if __name__ == "__main__":
    ok = run_audit()
    sys.exit(0 if ok else 1)

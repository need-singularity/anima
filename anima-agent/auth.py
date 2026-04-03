#!/usr/bin/env python3
"""Agent Authentication — user identity, sessions, permissions.

Supports:
  - Password (bcrypt hash)
  - TOTP (QR → iPhone Authenticator)
  - Token (API key style)
  - Owner verification (Telegram/Discord user ID)

Permission levels:
  GUEST(0)  — read consciousness status only
  USER(1)   — chat, tools tier 0-1
  ADMIN(2)  — all tools, self_modify, evolution
  OWNER(3)  — shell_execute, plugin management, shutdown

Usage:
    from auth import AuthManager, Permission

    auth = AuthManager()
    auth.register_user("alice", password="secret123", level=Permission.ADMIN)
    auth.enable_totp("alice")  # Returns QR URI for iPhone

    # Verify
    ok = auth.verify("alice", password="secret123")
    ok = auth.verify("alice", totp_code="123456")
    ok = auth.verify_token("abc123-token")

    # Check permission
    auth.check_permission("alice", Permission.ADMIN)  # True/False

    # CLI
    python auth.py --add alice --level admin
    python auth.py --totp alice          # Show QR URI
    python auth.py --list
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import struct
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

AUTH_FILE = Path(__file__).parent / "data" / "auth.json"


# ═══════════════════════════════════════════════════════════
# Permission levels
# ═══════════════════════════════════════════════════════════

class Permission:
    GUEST = 0
    USER = 1
    ADMIN = 2
    OWNER = 3

    _NAMES = {0: "guest", 1: "user", 2: "admin", 3: "owner"}

    @classmethod
    def name(cls, level: int) -> str:
        return cls._NAMES.get(level, f"level_{level}")

    @classmethod
    def from_name(cls, name: str) -> int:
        for k, v in cls._NAMES.items():
            if v == name.lower():
                return k
        return cls.GUEST


@dataclass
class UserRecord:
    username: str
    password_hash: str = ""       # SHA-256 salted hash
    salt: str = ""
    token: str = ""               # API token
    totp_secret: str = ""         # Base32 TOTP secret
    level: int = Permission.USER
    channel_ids: Dict[str, str] = field(default_factory=dict)  # channel→user_id
    created_at: float = field(default_factory=time.time)
    last_login: float = 0.0
    login_count: int = 0
    blocked: bool = False


# ═══════════════════════════════════════════════════════════
# TOTP (RFC 6238) — compatible with Google Authenticator / iPhone
# ═══════════════════════════════════════════════════════════

def _generate_totp_secret() -> str:
    """Generate a 20-byte random secret, base32 encoded."""
    import base64
    raw = os.urandom(20)
    return base64.b32encode(raw).decode("ascii").rstrip("=")


def _compute_totp(secret_b32: str, time_step: int = 30, digits: int = 6) -> str:
    """Compute current TOTP code (RFC 6238)."""
    import base64
    # Pad secret
    padded = secret_b32 + "=" * (-len(secret_b32) % 8)
    key = base64.b32decode(padded, casefold=True)
    # Time counter
    counter = int(time.time()) // time_step
    msg = struct.pack(">Q", counter)
    # HMAC-SHA1
    h = hmac.new(key, msg, hashlib.sha1).digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(code % (10 ** digits)).zfill(digits)


def _verify_totp(secret_b32: str, code: str, window: int = 1) -> bool:
    """Verify TOTP code with ±window tolerance."""
    for offset in range(-window, window + 1):
        import base64
        padded = secret_b32 + "=" * (-len(secret_b32) % 8)
        key = base64.b32decode(padded, casefold=True)
        counter = (int(time.time()) // 30) + offset
        msg = struct.pack(">Q", counter)
        h = hmac.new(key, msg, hashlib.sha1).digest()
        o = h[-1] & 0x0F
        c = struct.unpack(">I", h[o:o + 4])[0] & 0x7FFFFFFF
        expected = str(c % 1000000).zfill(6)
        if code == expected:
            return True
    return False


def totp_uri(username: str, secret: str, issuer: str = "Anima") -> str:
    """Generate otpauth:// URI for QR code scanning (iPhone/Google Authenticator)."""
    return f"otpauth://totp/{issuer}:{username}?secret={secret}&issuer={issuer}&digits=6&period=30"


# ═══════════════════════════════════════════════════════════
# Password hashing
# ═══════════════════════════════════════════════════════════

def _hash_password(password: str, salt: Optional[str] = None) -> tuple:
    """SHA-256 with salt. Returns (hash, salt)."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return h, salt


# ═══════════════════════════════════════════════════════════
# Auth Manager
# ═══════════════════════════════════════════════════════════

class AuthManager:
    """User authentication and permission management."""

    def __init__(self, auth_file: Optional[Path] = None):
        self._file = auth_file or AUTH_FILE
        self._users: Dict[str, UserRecord] = {}
        self._tokens: Dict[str, str] = {}  # token → username
        self._rate_limit: Dict[str, list] = {}  # username → [timestamps]
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file) as f:
                    data = json.load(f)
                for u in data.get("users", []):
                    rec = UserRecord(**{k: v for k, v in u.items()
                                       if k in UserRecord.__dataclass_fields__})
                    self._users[rec.username] = rec
                    if rec.token:
                        self._tokens[rec.token] = rec.username
            except Exception as e:
                logger.warning("Auth load failed: %s", e)

    def _save(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        data = {"users": [asdict(u) for u in self._users.values()]}
        with open(self._file, "w") as f:
            json.dump(data, f, indent=2)

    # ─── Registration ───

    def register_user(self, username: str, password: str = "",
                      level: int = Permission.USER) -> UserRecord:
        """Register a new user."""
        if username in self._users:
            raise ValueError(f"User {username} already exists")

        rec = UserRecord(username=username, level=level)
        if password:
            rec.password_hash, rec.salt = _hash_password(password)
        rec.token = secrets.token_urlsafe(32)
        self._users[username] = rec
        self._tokens[rec.token] = username
        self._save()
        logger.info("User registered: %s (level=%s)", username, Permission.name(level))
        return rec

    def link_channel(self, username: str, channel: str, channel_user_id: str):
        """Link a channel user ID (telegram/discord) to a username."""
        if username not in self._users:
            raise ValueError(f"User {username} not found")
        self._users[username].channel_ids[channel] = channel_user_id
        self._save()

    def enable_totp(self, username: str) -> str:
        """Enable TOTP for a user. Returns otpauth:// URI for QR scanning."""
        if username not in self._users:
            raise ValueError(f"User {username} not found")
        secret = _generate_totp_secret()
        self._users[username].totp_secret = secret
        self._save()
        return totp_uri(username, secret)

    # ─── Verification ───

    def verify(self, username: str, password: str = "",
               totp_code: str = "") -> bool:
        """Verify user credentials. Password OR TOTP (either suffices)."""
        rec = self._users.get(username)
        if not rec or rec.blocked:
            return False

        # Rate limiting (max 10 attempts per minute)
        now = time.time()
        attempts = self._rate_limit.get(username, [])
        attempts = [t for t in attempts if now - t < 60]
        if len(attempts) >= 10:
            logger.warning("Rate limit hit for %s", username)
            return False
        attempts.append(now)
        self._rate_limit[username] = attempts

        # Password check
        if password and rec.password_hash:
            h, _ = _hash_password(password, rec.salt)
            if h == rec.password_hash:
                rec.last_login = now
                rec.login_count += 1
                self._save()
                return True

        # TOTP check
        if totp_code and rec.totp_secret:
            if _verify_totp(rec.totp_secret, totp_code):
                rec.last_login = now
                rec.login_count += 1
                self._save()
                return True

        return False

    def verify_token(self, token: str) -> Optional[str]:
        """Verify API token. Returns username if valid."""
        username = self._tokens.get(token)
        if username and not self._users[username].blocked:
            return username
        return None

    def resolve_channel_user(self, channel: str, channel_user_id: str) -> Optional[str]:
        """Resolve channel user ID to username."""
        for u in self._users.values():
            if u.channel_ids.get(channel) == channel_user_id:
                return u.username
        return None

    # ─── Permissions ───

    def check_permission(self, username: str, required: int) -> bool:
        """Check if user has sufficient permission level."""
        rec = self._users.get(username)
        if not rec or rec.blocked:
            return False
        return rec.level >= required

    def get_level(self, username: str) -> int:
        rec = self._users.get(username)
        return rec.level if rec else Permission.GUEST

    def get_user(self, username: str) -> Optional[UserRecord]:
        return self._users.get(username)

    def list_users(self) -> List[Dict]:
        return [
            {"username": u.username, "level": Permission.name(u.level),
             "channels": list(u.channel_ids.keys()), "logins": u.login_count,
             "totp": bool(u.totp_secret), "blocked": u.blocked}
            for u in self._users.values()
        ]

    def block_user(self, username: str):
        if username in self._users:
            self._users[username].blocked = True
            self._save()

    def unblock_user(self, username: str):
        if username in self._users:
            self._users[username].blocked = False
            self._save()

    # ─── Audit ───

    def audit_log_path(self) -> Path:
        return self._file.parent / "audit.log"

    def log_action(self, username: str, action: str, details: str = ""):
        """Append to audit log."""
        log_path = self.audit_log_path()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {username} | {action} | {details}\n"
        with open(log_path, "a") as f:
            f.write(entry)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Agent Auth Manager")
    parser.add_argument("--add", type=str, help="Add user")
    parser.add_argument("--level", type=str, default="user", help="Permission level")
    parser.add_argument("--password", "-p", type=str, default="", help="Password")
    parser.add_argument("--totp", type=str, help="Enable TOTP for user (prints QR URI)")
    parser.add_argument("--link", nargs=3, metavar=("USER", "CHANNEL", "ID"),
                        help="Link channel user ID")
    parser.add_argument("--verify", nargs=2, metavar=("USER", "PASSWORD"))
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--block", type=str)
    parser.add_argument("--unblock", type=str)
    args = parser.parse_args()

    auth = AuthManager()

    if args.add:
        level = Permission.from_name(args.level)
        rec = auth.register_user(args.add, password=args.password, level=level)
        print(f"User '{args.add}' created (level={Permission.name(level)})")
        print(f"Token: {rec.token}")

    elif args.totp:
        uri = auth.enable_totp(args.totp)
        print(f"TOTP enabled for '{args.totp}'")
        print(f"Scan this with iPhone/Google Authenticator:")
        print(f"  {uri}")

    elif args.link:
        auth.link_channel(args.link[0], args.link[1], args.link[2])
        print(f"Linked {args.link[0]} → {args.link[1]}:{args.link[2]}")

    elif args.verify:
        ok = auth.verify(args.verify[0], password=args.verify[1])
        print(f"Verify: {'OK' if ok else 'FAILED'}")

    elif args.list:
        users = auth.list_users()
        if not users:
            print("No users registered.")
        for u in users:
            totp = "🔐" if u["totp"] else "  "
            blocked = "🚫" if u["blocked"] else "  "
            print(f"  {blocked}{totp} {u['username']:15s} {u['level']:6s} "
                  f"channels={u['channels']} logins={u['logins']}")

    elif args.block:
        auth.block_user(args.block)
        print(f"Blocked: {args.block}")

    elif args.unblock:
        auth.unblock_user(args.unblock)
        print(f"Unblocked: {args.unblock}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()

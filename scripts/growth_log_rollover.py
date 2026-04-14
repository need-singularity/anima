#!/usr/bin/env python3
# @hexa-first-exempt
# growth_log_rollover.py — CLM-P3-2
#
# Growth state files older than 30 days → cold archive tar.gz.
#
# Scan:  config/growth_loop_{archive,state}.json + logs/growth_*.log + .growth/
# Skip:  files modified within the last 30 days (active)
# Out:   <scan_dir>/_archive/growth_<YYYY-MM-DD>.tar.gz
# Safe:  sha256 verify each member inside .tar.gz BEFORE deleting originals.
# Atom:  tempfile + os.replace.  Idem: rerun = 0 mutations.
#
# Modes: --dry-run / --execute / --keep-original
#
# Exit codes:
#   0  ok (any combination of no-op / archived / verified)
#   1  error (gz build failed, sha mismatch, etc.)

import argparse
import datetime as dt
import glob
import hashlib
import json
import os
import sys
import tarfile
import tempfile
from collections import defaultdict

HOME = os.environ.get("HOME", os.path.expanduser("~"))
ANIMA = os.environ.get("ANIMA", os.path.join(HOME, "Dev", "anima"))

SCAN_DIRS = [
    os.path.join(ANIMA, "ready", "anima", "config"),
    os.path.join(ANIMA, "ready", "anima", "logs"),
    os.path.join(ANIMA, "logs"),
    os.path.join(ANIMA, ".growth"),
]

GROWTH_GLOBS = [
    "growth_loop_archive.json",
    "growth_loop_state.json",
    "growth_*.log",
    "growth.log",
]

CUTOFF_DAYS = 30


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_candidates(cutoff_ts: float):
    """Return dict[parent_dir] -> list[path] for files older than cutoff."""
    seen = set()
    groups = defaultdict(list)
    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for pat in GROWTH_GLOBS:
            for p in sorted(glob.glob(os.path.join(scan_dir, pat))):
                real = os.path.realpath(p)
                if real in seen:
                    continue
                seen.add(real)
                if not os.path.isfile(p):
                    continue
                try:
                    mt = os.path.getmtime(p)
                except OSError:
                    continue
                if mt < cutoff_ts:
                    groups[scan_dir].append(p)
    for k in groups:
        groups[k].sort()
    return groups


def date_tag_from_mtime(paths: list) -> str:
    """Pick the newest mtime among paths as the archive date tag."""
    newest = max(os.path.getmtime(p) for p in paths)
    return dt.date.fromtimestamp(newest).isoformat()


def build_archive(parent_dir: str, members: list, dry_run: bool):
    """Return dict with path, bytes, members, sha256_map, status."""
    archive_dir = os.path.join(parent_dir, "_archive")
    tag = date_tag_from_mtime(members)
    out_path = os.path.join(archive_dir, f"growth_{tag}.tar.gz")

    plan = {
        "parent": parent_dir,
        "archive": out_path,
        "members": [os.path.basename(m) for m in members],
        "member_count": len(members),
        "archive_exists": os.path.exists(out_path),
        "date_tag": tag,
    }

    if plan["archive_exists"]:
        plan["status"] = "skip-exists"
        return plan

    if dry_run:
        plan["status"] = "dry-run"
        plan["bytes"] = None
        return plan

    os.makedirs(archive_dir, exist_ok=True)

    # Pre-compute sha256 of source files for post-verification.
    source_sha = {}
    for m in members:
        source_sha[os.path.basename(m)] = sha256_file(m)

    # Atomic write via tempfile in same dir + os.replace.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".growth_{tag}_", suffix=".tar.gz.tmp", dir=archive_dir
    )
    os.close(fd)
    try:
        with tarfile.open(tmp_path, "w:gz", compresslevel=6) as tar:
            for m in members:
                tar.add(m, arcname=os.path.basename(m))
        os.replace(tmp_path, out_path)
    except Exception as e:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass
        plan["status"] = f"error: tar build failed: {e}"
        return plan

    if os.path.getsize(out_path) == 0:
        plan["status"] = "error: gz size zero"
        return plan

    # Verify: read archive back, compare sha256 of each member to source.
    verified = {}
    try:
        with tarfile.open(out_path, "r:gz") as tar:
            for name, expected in source_sha.items():
                ti = tar.getmember(name)
                f = tar.extractfile(ti)
                if f is None:
                    plan["status"] = f"error: no readable member {name}"
                    return plan
                got = sha256_bytes(f.read())
                if got != expected:
                    plan["status"] = (
                        f"error: sha mismatch {name} "
                        f"expect={expected} got={got}"
                    )
                    return plan
                verified[name] = got
    except Exception as e:
        plan["status"] = f"error: gz verify failed: {e}"
        return plan

    plan["sha256_map"] = verified
    plan["bytes"] = os.path.getsize(out_path)
    plan["gz_sha256"] = sha256_file(out_path)
    plan["status"] = "verified"
    return plan


def main():
    ap = argparse.ArgumentParser(
        description="growth state 30-day rollover (CLM-P3-2)"
    )
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run", action="store_true", help="plan only, no mutations"
    )
    mode.add_argument(
        "--execute", action="store_true", help="actually archive + delete"
    )
    ap.add_argument(
        "--keep-original",
        action="store_true",
        help="keep source files even after successful archive",
    )
    ap.add_argument(
        "--cutoff-days",
        type=int,
        default=CUTOFF_DAYS,
        help=f"age threshold in days (default {CUTOFF_DAYS})",
    )
    ap.add_argument(
        "--today",
        default=None,
        help="override today YYYY-MM-DD (testing)",
    )
    ap.add_argument(
        "--json", action="store_true", help="emit JSON summary"
    )
    args = ap.parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True  # default safe

    today = (
        dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    )
    cutoff = dt.datetime(today.year, today.month, today.day) - dt.timedelta(
        days=args.cutoff_days
    )
    cutoff_ts = cutoff.timestamp()

    groups = collect_candidates(cutoff_ts)
    total_files = sum(len(v) for v in groups.values())

    summary = {
        "today": today.isoformat(),
        "cutoff_date": cutoff.date().isoformat(),
        "cutoff_days": args.cutoff_days,
        "mode": "dry-run" if args.dry_run else "execute",
        "keep_original": args.keep_original,
        "scan_dirs": SCAN_DIRS,
        "files_found": total_files,
        "dir_groups": len(groups),
        "archives": [],
        "originals_deleted": [],
        "errors": [],
    }

    for parent_dir in sorted(groups.keys()):
        members = groups[parent_dir]
        plan = build_archive(parent_dir, members, dry_run=args.dry_run)
        summary["archives"].append(plan)
        if plan.get("status", "").startswith("error"):
            summary["errors"].append(plan["status"])
            continue
        if (
            args.execute
            and plan["status"] == "verified"
            and not args.keep_original
        ):
            for m in members:
                try:
                    os.remove(m)
                    summary["originals_deleted"].append(
                        os.path.basename(m)
                    )
                except OSError as e:
                    summary["errors"].append(f"delete_fail {m}: {e}")

    total_bytes = sum(
        a.get("bytes") or 0
        for a in summary["archives"]
        if a.get("bytes")
    )
    summary["total_bytes_archived"] = total_bytes

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(
            f"growth_log_rollover: today={summary['today']} "
            f"cutoff={summary['cutoff_date']} mode={summary['mode']}"
        )
        print(f"  cutoff days:      {args.cutoff_days}")
        print(f"  files found:      {summary['files_found']}")
        print(f"  dir groups:       {summary['dir_groups']}")
        for a in summary["archives"]:
            bstr = f"  {a['bytes']}B" if a.get("bytes") else ""
            print(
                f"    {a['parent']}: {a['member_count']} files "
                f"-> {os.path.basename(a['archive'])}  "
                f"[{a['status']}]{bstr}"
            )
        if summary["originals_deleted"]:
            print(
                f"  deleted originals: "
                f"{len(summary['originals_deleted'])}"
            )
        if summary["errors"]:
            print("  ERRORS:")
            for e in summary["errors"]:
                print(f"    {e}")

    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

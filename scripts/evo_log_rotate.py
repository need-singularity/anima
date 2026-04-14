#!/usr/bin/env python3
# @hexa-first-exempt
# evo_log_rotate.py — CLM-P3-3
#
# evo_*.log → ISO week tar.gz archives.
#
# Scan:  $ANIMA/ready/anima/logs/evo_*.log
# Group: ISO year-week from file mtime
# Skip:  current ISO week (active logs)
# Out:   $ANIMA/ready/anima/logs/_archive/evo_<YYYY>-W<WW>.tar.gz
# Safe:  sha256 verify each member inside the .tar.gz BEFORE deleting originals.
# Atom:  tempfile + os.replace.
# Idem:  rerun with no new input produces 0 mutations.
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
LOG_DIR = os.path.join(ANIMA, "ready", "anima", "logs")
ARCHIVE_DIR = os.path.join(LOG_DIR, "_archive")


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


def iso_week_key(ts: float) -> str:
    d = dt.date.fromtimestamp(ts)
    iso = d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def current_week_monday(today: dt.date) -> dt.date:
    return today - dt.timedelta(days=today.weekday())


def scan(today: dt.date):
    """Return (groups, skipped_current_week, scanned_paths).

    groups: dict[week_key] -> list[path]
    """
    paths = sorted(glob.glob(os.path.join(LOG_DIR, "evo_*.log")))
    monday = current_week_monday(today)
    monday_ts = dt.datetime(monday.year, monday.month, monday.day).timestamp()

    groups = defaultdict(list)
    skipped = []
    for p in paths:
        try:
            mt = os.path.getmtime(p)
        except OSError:
            continue
        if mt >= monday_ts:
            skipped.append((p, mt))
            continue
        groups[iso_week_key(mt)].append(p)
    for k in groups:
        groups[k].sort()
    return groups, skipped, paths


def build_archive(week_key: str, members: list, dry_run: bool):
    """Return dict with path, bytes, members, sha256_map, status."""
    out_path = os.path.join(ARCHIVE_DIR, f"evo_{week_key}.tar.gz")
    plan = {
        "week": week_key,
        "archive": out_path,
        "members": [os.path.basename(m) for m in members],
        "member_count": len(members),
        "archive_exists": os.path.exists(out_path),
    }
    if dry_run:
        plan["status"] = "dry-run"
        plan["bytes"] = None
        return plan

    os.makedirs(ARCHIVE_DIR, exist_ok=True)

    # Pre-compute sha256 of source files — this is what we verify AFTER.
    source_sha = {}
    for m in members:
        source_sha[os.path.basename(m)] = sha256_file(m)

    # Atomic write via tempfile in same dir + os.replace.
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".evo_{week_key}_", suffix=".tar.gz.tmp", dir=ARCHIVE_DIR
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
                    plan["status"] = f"error: sha mismatch {name} expect={expected} got={got}"
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
    ap = argparse.ArgumentParser(description="evo log ISO-week rotator (CLM-P3-3)")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="plan only, no mutations")
    mode.add_argument("--execute", action="store_true", help="actually rotate")
    ap.add_argument("--keep-original", action="store_true",
                    help="keep source files even after successful archive")
    ap.add_argument("--today", default=None,
                    help="override today YYYY-MM-DD (testing)")
    ap.add_argument("--json", action="store_true", help="emit JSON summary")
    args = ap.parse_args()

    if not args.dry_run and not args.execute:
        args.dry_run = True  # default safe

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()

    groups, skipped, paths = scan(today)
    summary = {
        "today": today.isoformat(),
        "current_iso_week": iso_week_key(
            dt.datetime(today.year, today.month, today.day).timestamp()
        ),
        "log_dir": LOG_DIR,
        "archive_dir": ARCHIVE_DIR,
        "mode": "dry-run" if args.dry_run else "execute",
        "keep_original": args.keep_original,
        "files_scanned": len(paths),
        "files_skipped_current_week": len(skipped),
        "weeks_grouped": len(groups),
        "archives": [],
        "originals_deleted": [],
        "errors": [],
    }

    for week_key in sorted(groups.keys()):
        members = groups[week_key]
        plan = build_archive(week_key, members, dry_run=args.dry_run)
        summary["archives"].append(plan)
        if plan.get("status", "").startswith("error"):
            summary["errors"].append(plan["status"])
            continue
        if args.execute and plan["status"] == "verified" and not args.keep_original:
            for m in members:
                try:
                    os.remove(m)
                    summary["originals_deleted"].append(os.path.basename(m))
                except OSError as e:
                    summary["errors"].append(f"delete_fail {m}: {e}")

    total_bytes = sum(
        a.get("bytes") or 0 for a in summary["archives"] if a.get("bytes")
    )
    summary["total_bytes_archived"] = total_bytes

    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print(f"evo_log_rotate: today={summary['today']} mode={summary['mode']}")
        print(f"  scan dir:         {LOG_DIR}")
        print(f"  archive dir:      {ARCHIVE_DIR}")
        print(f"  files scanned:    {summary['files_scanned']}")
        print(f"  current-week skip:{summary['files_skipped_current_week']}")
        print(f"  weeks grouped:    {summary['weeks_grouped']}")
        for a in summary["archives"]:
            print(f"    {a['week']}: {a['member_count']} files -> {os.path.basename(a['archive'])}  [{a['status']}]"
                  + (f"  {a['bytes']}B" if a.get("bytes") else ""))
        if summary["originals_deleted"]:
            print(f"  deleted originals: {len(summary['originals_deleted'])}")
        if summary["errors"]:
            print("  ERRORS:")
            for e in summary["errors"]:
                print(f"    {e}")
    return 1 if summary["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())

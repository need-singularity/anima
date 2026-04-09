#!/usr/bin/env python3
"""Organize EEG recordings into structured directories with SQLite index.

Scans recordings/ for flat files, parses timestamps from filenames,
moves them into structured directories, and maintains a SQLite index.

Directory structure:
  recordings/
  ├── sessions/
  │   └── YYYY-MM-DD_HHMMSS/
  │       ├── eeg_data.json
  │       ├── consciousness_data.json
  │       └── metadata.json
  ├── validations/
  │   ├── validation_YYYYMMDD_HHMMSS.json
  │   └── validation_history.csv
  ├── protocols/
  │   ├── nback/
  │   └── meditation/
  └── index.db  (SQLite)

Usage:
  python organize_recordings.py                          # Organize flat files
  python organize_recordings.py --dry-run                # Preview changes
  python organize_recordings.py --query "protocol=nback" # Search index
  python organize_recordings.py --stats                  # Show index stats
  python organize_recordings.py --reindex                # Rebuild index from dirs
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


# ═══════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════

SCRIPT_DIR = Path(__file__).resolve().parent
EEG_ROOT = SCRIPT_DIR.parent
RECORDINGS_DIR = EEG_ROOT / 'recordings'
SESSIONS_DIR = RECORDINGS_DIR / 'sessions'
VALIDATIONS_DIR = RECORDINGS_DIR / 'validations'
PROTOCOLS_DIR = RECORDINGS_DIR / 'protocols'
INDEX_DB = RECORDINGS_DIR / 'index.db'

# Timestamp patterns in filenames
TIMESTAMP_PATTERNS = [
    # YYYYMMDD_HHMMSS
    (re.compile(r'(\d{8}_\d{6})'), '%Y%m%d_%H%M%S'),
    # YYYY-MM-DD_HHMMSS
    (re.compile(r'(\d{4}-\d{2}-\d{2}_\d{6})'), '%Y-%m-%d_%H%M%S'),
    # YYYY-MM-DD_HH-MM-SS
    (re.compile(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})'), '%Y-%m-%d_%H-%M-%S'),
    # YYYYMMDD
    (re.compile(r'(\d{8})'), '%Y%m%d'),
]

# File type classification
FILE_CATEGORIES = {
    'validation': re.compile(r'validation', re.IGNORECASE),
    'eeg': re.compile(r'eeg|brainflow|openbci', re.IGNORECASE),
    'consciousness': re.compile(r'consciousness|phi|tension', re.IGNORECASE),
    'nback': re.compile(r'nback|n-back|n_back', re.IGNORECASE),
    'meditation': re.compile(r'meditat', re.IGNORECASE),
    'session': re.compile(r'session|recording|capture', re.IGNORECASE),
}


# ═══════════════════════════════════════════════════════════
# SQLite Index
# ═══════════════════════════════════════════════════════════

def init_db(db_path: Path) -> sqlite3.Connection:
    """Initialize or open the SQLite index database."""
    conn = sqlite3.connect(str(db_path))
    conn.execute('''
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            protocol TEXT DEFAULT 'unknown',
            category TEXT DEFAULT 'session',
            duration_s REAL DEFAULT 0,
            brain_like_pct REAL DEFAULT 0,
            cells INTEGER DEFAULT 0,
            steps INTEGER DEFAULT 0,
            file_paths TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON recordings(timestamp)
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_protocol ON recordings(protocol)
    ''')
    conn.execute('''
        CREATE INDEX IF NOT EXISTS idx_category ON recordings(category)
    ''')
    conn.commit()
    return conn


def insert_recording(conn: sqlite3.Connection, session_id: str, timestamp: str,
                     protocol: str, category: str, file_paths: List[str],
                     duration_s: float = 0, brain_like_pct: float = 0,
                     cells: int = 0, steps: int = 0, notes: str = '') -> int:
    """Insert a recording entry into the index."""
    cur = conn.execute('''
        INSERT INTO recordings (session_id, timestamp, protocol, category,
                                duration_s, brain_like_pct, cells, steps,
                                file_paths, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, timestamp, protocol, category, duration_s,
          brain_like_pct, cells, steps, json.dumps(file_paths), notes))
    conn.commit()
    return cur.lastrowid


def query_recordings(conn: sqlite3.Connection, query_str: str) -> List[dict]:
    """Query recordings by key=value pairs.

    Examples:
        "protocol=nback"
        "category=validation"
        "brain_like_pct>50"
        "timestamp>2026-03-01"
    """
    # Parse query
    results = []
    conditions = []
    params = []

    for part in query_str.split(','):
        part = part.strip()
        if not part:
            continue

        # Support operators: =, >, <, >=, <=, !=
        for op in ['>=', '<=', '!=', '>', '<', '=']:
            if op in part:
                key, val = part.split(op, 1)
                key = key.strip()
                val = val.strip()

                # Validate column name
                valid_cols = ['session_id', 'timestamp', 'protocol', 'category',
                              'duration_s', 'brain_like_pct', 'cells', 'steps', 'notes']
                if key not in valid_cols:
                    print(f"  Warning: unknown column '{key}', skipping")
                    break

                sql_op = op if op != '=' else '='
                if key in ('duration_s', 'brain_like_pct', 'cells', 'steps'):
                    try:
                        val = float(val)
                    except ValueError:
                        pass

                if op == '=' and isinstance(val, str):
                    conditions.append(f"{key} LIKE ?")
                    params.append(f"%{val}%")
                else:
                    conditions.append(f"{key} {sql_op} ?")
                    params.append(val)
                break

    where = ' AND '.join(conditions) if conditions else '1=1'
    sql = f"SELECT * FROM recordings WHERE {where} ORDER BY timestamp DESC LIMIT 100"

    cur = conn.execute(sql, params)
    cols = [desc[0] for desc in cur.description]
    for row in cur.fetchall():
        results.append(dict(zip(cols, row)))

    return results


# ═══════════════════════════════════════════════════════════
# File Organization
# ═══════════════════════════════════════════════════════════

def parse_timestamp(filename: str) -> Optional[datetime]:
    """Extract timestamp from filename."""
    for pattern, fmt in TIMESTAMP_PATTERNS:
        match = pattern.search(filename)
        if match:
            try:
                return datetime.strptime(match.group(1), fmt)
            except ValueError:
                continue
    return None


def classify_file(filepath: Path) -> Tuple[str, str]:
    """Classify a file into (category, protocol).

    Returns: (category, protocol)
      category: 'validation', 'session', 'protocol'
      protocol: 'nback', 'meditation', 'unknown'
    """
    name = filepath.name.lower()

    # Check validation files first
    if FILE_CATEGORIES['validation'].search(name):
        return 'validation', 'validation'

    # Check protocol-specific files
    if FILE_CATEGORIES['nback'].search(name):
        return 'protocol', 'nback'
    if FILE_CATEGORIES['meditation'].search(name):
        return 'protocol', 'meditation'

    # Default to session
    return 'session', 'unknown'


def extract_metadata_from_json(filepath: Path) -> dict:
    """Try to extract metadata from a JSON file."""
    meta = {}
    try:
        with open(filepath) as f:
            data = json.load(f)
        if isinstance(data, dict):
            meta['brain_like_pct'] = data.get('brain_like_percent', 0)
            meta['cells'] = data.get('cells', 0)
            meta['steps'] = data.get('steps', 0)
            meta['duration_s'] = data.get('duration_s', 0)
    except (json.JSONDecodeError, KeyError, TypeError):
        pass
    return meta


def scan_flat_files(recordings_dir: Path) -> List[Path]:
    """Find flat files in recordings/ that should be organized."""
    flat_files = []

    # Only look at top-level files (not already in subdirectories)
    if not recordings_dir.exists():
        return flat_files

    for item in recordings_dir.iterdir():
        if item.is_file() and item.name != 'index.db' and item.name != '.gitkeep':
            # Skip CSV history files
            if item.name == 'validation_history.csv':
                continue
            flat_files.append(item)

    return flat_files


def organize_file(filepath: Path, dry_run: bool = False) -> Optional[dict]:
    """Organize a single file into the structured directory.

    Returns metadata dict if successful, None if skipped.
    """
    filename = filepath.name
    timestamp = parse_timestamp(filename)
    category, protocol = classify_file(filepath)

    if timestamp is None:
        # Use file modification time as fallback
        mtime = filepath.stat().st_mtime
        timestamp = datetime.fromtimestamp(mtime)

    session_id = timestamp.strftime('%Y-%m-%d_%H%M%S')

    # Determine destination
    if category == 'validation':
        dest_dir = VALIDATIONS_DIR
        dest_path = dest_dir / filename
    elif category == 'protocol':
        dest_dir = PROTOCOLS_DIR / protocol
        dest_path = dest_dir / filename
    else:
        # Session: create session directory
        dest_dir = SESSIONS_DIR / session_id
        dest_path = dest_dir / filename

    # Extract metadata if JSON
    meta = {}
    if filepath.suffix in ('.json',):
        meta = extract_metadata_from_json(filepath)

    result = {
        'source': str(filepath),
        'destination': str(dest_path),
        'session_id': session_id,
        'timestamp': timestamp.isoformat(),
        'category': category,
        'protocol': protocol,
        **meta,
    }

    if dry_run:
        print(f"  [DRY RUN] {filepath.name}")
        print(f"    -> {dest_path.relative_to(RECORDINGS_DIR)}")
        print(f"    Category: {category}, Protocol: {protocol}, Time: {session_id}")
        return result

    # Create destination directory
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Move file
    if filepath != dest_path:
        shutil.move(str(filepath), str(dest_path))
        print(f"  Moved: {filepath.name} -> {dest_path.relative_to(RECORDINGS_DIR)}")

    # Create metadata.json for sessions
    if category == 'session':
        meta_file = dest_dir / 'metadata.json'
        if not meta_file.exists():
            metadata = {
                'session_id': session_id,
                'timestamp': timestamp.isoformat(),
                'protocol': protocol,
                'files': [filename],
                **meta,
            }
            with open(meta_file, 'w') as f:
                json.dump(metadata, f, indent=2)
        else:
            # Append filename to existing metadata
            try:
                with open(meta_file) as f:
                    existing = json.load(f)
                if filename not in existing.get('files', []):
                    existing.setdefault('files', []).append(filename)
                    with open(meta_file, 'w') as f:
                        json.dump(existing, f, indent=2)
            except (json.JSONDecodeError, KeyError):
                pass

    return result


# ═══════════════════════════════════════════════════════════
# Reindex
# ═══════════════════════════════════════════════════════════

def reindex(conn: sqlite3.Connection):
    """Rebuild the index from the directory structure."""
    # Clear existing entries
    conn.execute('DELETE FROM recordings')
    conn.commit()

    count = 0

    # Index sessions
    if SESSIONS_DIR.exists():
        for session_dir in sorted(SESSIONS_DIR.iterdir()):
            if not session_dir.is_dir() or session_dir.name.startswith('.'):
                continue

            meta_file = session_dir / 'metadata.json'
            meta = {}
            if meta_file.exists():
                try:
                    with open(meta_file) as f:
                        meta = json.load(f)
                except (json.JSONDecodeError, KeyError):
                    pass

            files = [str(f.relative_to(RECORDINGS_DIR)) for f in session_dir.iterdir()
                     if f.is_file() and f.name != '.gitkeep']

            if files:
                insert_recording(
                    conn,
                    session_id=session_dir.name,
                    timestamp=meta.get('timestamp', session_dir.name),
                    protocol=meta.get('protocol', 'unknown'),
                    category='session',
                    file_paths=files,
                    duration_s=meta.get('duration_s', 0),
                    brain_like_pct=meta.get('brain_like_pct', 0),
                    cells=meta.get('cells', 0),
                    steps=meta.get('steps', 0),
                )
                count += 1

    # Index validations
    if VALIDATIONS_DIR.exists():
        for vfile in sorted(VALIDATIONS_DIR.iterdir()):
            if not vfile.is_file() or vfile.name.startswith('.') or vfile.suffix == '.csv':
                continue

            timestamp = parse_timestamp(vfile.name)
            meta = {}
            if vfile.suffix == '.json':
                meta = extract_metadata_from_json(vfile)

            session_id = timestamp.strftime('%Y-%m-%d_%H%M%S') if timestamp else vfile.stem

            insert_recording(
                conn,
                session_id=session_id,
                timestamp=timestamp.isoformat() if timestamp else '',
                protocol='validation',
                category='validation',
                file_paths=[str(vfile.relative_to(RECORDINGS_DIR))],
                brain_like_pct=meta.get('brain_like_pct', 0),
                cells=meta.get('cells', 0),
                steps=meta.get('steps', 0),
            )
            count += 1

    # Index protocol recordings
    if PROTOCOLS_DIR.exists():
        for proto_dir in sorted(PROTOCOLS_DIR.iterdir()):
            if not proto_dir.is_dir() or proto_dir.name.startswith('.'):
                continue

            protocol = proto_dir.name
            for pfile in sorted(proto_dir.iterdir()):
                if not pfile.is_file() or pfile.name.startswith('.'):
                    continue

                timestamp = parse_timestamp(pfile.name)
                meta = {}
                if pfile.suffix == '.json':
                    meta = extract_metadata_from_json(pfile)

                session_id = timestamp.strftime('%Y-%m-%d_%H%M%S') if timestamp else pfile.stem

                insert_recording(
                    conn,
                    session_id=session_id,
                    timestamp=timestamp.isoformat() if timestamp else '',
                    protocol=protocol,
                    category='protocol',
                    file_paths=[str(pfile.relative_to(RECORDINGS_DIR))],
                    brain_like_pct=meta.get('brain_like_pct', 0),
                    cells=meta.get('cells', 0),
                    steps=meta.get('steps', 0),
                )
                count += 1

    print(f"  Reindexed {count} recordings.")


# ═══════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════

def print_stats(conn: sqlite3.Connection):
    """Print index statistics."""
    print()
    print("  ┌─────────────────────────────────────────────┐")
    print("  │        EEG Recordings Index Stats           │")
    print("  └─────────────────────────────────────────────┘")
    print()

    total = conn.execute('SELECT COUNT(*) FROM recordings').fetchone()[0]
    print(f"  Total recordings: {total}")

    if total == 0:
        print("  (no recordings indexed)")
        return

    # By category
    print()
    print("  By category:")
    for row in conn.execute('SELECT category, COUNT(*) FROM recordings GROUP BY category ORDER BY COUNT(*) DESC'):
        bar = '#' * min(40, row[1])
        print(f"    {row[0]:<15} {bar} {row[1]}")

    # By protocol
    print()
    print("  By protocol:")
    for row in conn.execute('SELECT protocol, COUNT(*) FROM recordings GROUP BY protocol ORDER BY COUNT(*) DESC'):
        bar = '#' * min(40, row[1])
        print(f"    {row[0]:<15} {bar} {row[1]}")

    # Brain-like % stats (for validations)
    val_stats = conn.execute('''
        SELECT AVG(brain_like_pct), MIN(brain_like_pct), MAX(brain_like_pct), COUNT(*)
        FROM recordings WHERE category='validation' AND brain_like_pct > 0
    ''').fetchone()

    if val_stats and val_stats[3] > 0:
        print()
        print("  Validation brain-like % stats:")
        print(f"    Mean: {val_stats[0]:.1f}%  Min: {val_stats[1]:.1f}%  Max: {val_stats[2]:.1f}%  Count: {val_stats[3]}")

    # Date range
    date_range = conn.execute('''
        SELECT MIN(timestamp), MAX(timestamp) FROM recordings WHERE timestamp != ''
    ''').fetchone()

    if date_range and date_range[0]:
        print()
        print(f"  Date range: {date_range[0][:10]} to {date_range[1][:10]}")

    print()


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description='Organize EEG recordings into structured directories with SQLite index'
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Preview changes without moving files')
    parser.add_argument('--query', type=str, default=None,
                        help='Query the index (e.g., "protocol=nback", "brain_like_pct>50")')
    parser.add_argument('--stats', action='store_true',
                        help='Show index statistics')
    parser.add_argument('--reindex', action='store_true',
                        help='Rebuild index from directory structure')
    args = parser.parse_args()

    # Ensure base directories exist
    for d in [SESSIONS_DIR, VALIDATIONS_DIR, PROTOCOLS_DIR / 'nback', PROTOCOLS_DIR / 'meditation']:
        d.mkdir(parents=True, exist_ok=True)

    # Open/create database
    conn = init_db(INDEX_DB)

    if args.query:
        print(f"\n  Querying: {args.query}")
        print()
        results = query_recordings(conn, args.query)
        if not results:
            print("  No results found.")
        else:
            # Print table
            print(f"  {'ID':>4} | {'Session':^19} | {'Protocol':^12} | {'Category':^12} | {'Brain%':>7} | {'Files':^30}")
            print(f"  {'-'*4}-+-{'-'*19}-+-{'-'*12}-+-{'-'*12}-+-{'-'*7}-+-{'-'*30}")
            for r in results:
                files_str = r.get('file_paths', '[]')
                try:
                    files = json.loads(files_str)
                    files_short = ', '.join(Path(f).name for f in files[:2])
                    if len(files) > 2:
                        files_short += f' +{len(files)-2}'
                except (json.JSONDecodeError, TypeError):
                    files_short = str(files_str)[:30]

                print(f"  {r['id']:>4} | {r['session_id']:^19} | {r['protocol']:^12} | "
                      f"{r['category']:^12} | {r.get('brain_like_pct', 0):>6.1f}% | {files_short}")
            print(f"\n  Total: {len(results)} result(s)")
        conn.close()
        return

    if args.stats:
        print_stats(conn)
        conn.close()
        return

    if args.reindex:
        print("\n  Rebuilding index from directory structure...")
        reindex(conn)
        print_stats(conn)
        conn.close()
        return

    # Default: organize flat files
    print("\n  Scanning for flat files in recordings/...")
    flat_files = scan_flat_files(RECORDINGS_DIR)

    if not flat_files:
        print("  No flat files found to organize.")
        print("  (Files already in sessions/, validations/, or protocols/ are left in place.)")
        print()
        print("  Use --reindex to rebuild the SQLite index from existing directories.")
        print("  Use --stats to see current index statistics.")
        print("  Use --query 'protocol=nback' to search the index.")
        conn.close()
        return

    print(f"  Found {len(flat_files)} file(s) to organize:")
    print()

    organized = []
    for fpath in sorted(flat_files):
        result = organize_file(fpath, dry_run=args.dry_run)
        if result:
            organized.append(result)

    if not args.dry_run and organized:
        # Index organized files
        print()
        print("  Updating SQLite index...")
        for entry in organized:
            insert_recording(
                conn,
                session_id=entry['session_id'],
                timestamp=entry['timestamp'],
                protocol=entry['protocol'],
                category=entry['category'],
                file_paths=[entry['destination']],
                brain_like_pct=entry.get('brain_like_pct', 0),
                cells=entry.get('cells', 0),
                steps=entry.get('steps', 0),
            )
        print(f"  Indexed {len(organized)} recording(s).")

    print()
    if args.dry_run:
        print(f"  [DRY RUN] Would organize {len(organized)} file(s). No changes made.")
    else:
        print(f"  Organized {len(organized)} file(s).")

    conn.close()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Upload checkpoints and corpus files to Cloudflare R2.

Usage:
  python scripts/r2_upload.py --checkpoint v14_128c_final           # upload all .pt in dir
  python scripts/r2_upload.py --checkpoint v14_128c_final --best    # best.pt only
  python scripts/r2_upload.py --corpus v6
  python scripts/r2_upload.py --list                                # list R2 contents
  python scripts/r2_upload.py --download v14_128c_final/best.pt     # download from R2
  python scripts/r2_upload.py --prune --keep 3                      # keep latest 3 versions
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Load env before boto3
ROOT = Path(__file__).resolve().parent.parent / "anima"
ENV_FILE = ROOT / ".env"
LOCAL_ENV = ROOT / ".local" / ".env"

def load_env():
    """Load .env files (local overrides root)."""
    for env_path in [ENV_FILE, LOCAL_ENV]:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                os.environ.setdefault(key, value)

load_env()

import boto3
from botocore.config import Config

BUCKET = os.environ.get("ANIMA_R2_BUCKET", "anima")
ENDPOINT = os.environ.get("ANIMA_R2_ENDPOINT")
ACCESS_KEY = os.environ.get("ANIMA_R2_ACCESS_KEY")
SECRET_KEY = os.environ.get("ANIMA_R2_SECRET_KEY")

CHECKPOINTS_DIR = ROOT / "checkpoints"


def get_s3():
    if not all([ENDPOINT, ACCESS_KEY, SECRET_KEY]):
        sys.exit("R2 credentials not configured. Set ANIMA_R2_ENDPOINT/ACCESS_KEY/SECRET_KEY in .env")
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "adaptive"}),
        region_name="auto",
    )


def md5sum(path: Path) -> str:
    """Compute MD5 for integrity verification."""
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def upload_file(s3, local: Path, key: str, metadata: dict = None):
    """Upload with progress and integrity check."""
    size_mb = local.stat().st_size / 1024 / 1024
    print(f"  Uploading {local.name} ({size_mb:.1f} MB) -> r2://{BUCKET}/{key}")

    local_md5 = md5sum(local)
    extra = {"Metadata": {"md5": local_md5, "uploaded_at": datetime.now(timezone.utc).isoformat()}}
    if metadata:
        extra["Metadata"].update({k: str(v) for k, v in metadata.items()})

    t0 = time.time()
    # Use multipart for large files
    from boto3.s3.transfer import TransferConfig
    config = TransferConfig(
        multipart_threshold=50 * 1024 * 1024,  # 50MB
        multipart_chunksize=50 * 1024 * 1024,
        max_concurrency=4,
    )
    s3.upload_file(str(local), BUCKET, key, ExtraArgs=extra, Config=config)
    elapsed = time.time() - t0
    speed = size_mb / elapsed if elapsed > 0 else 0
    print(f"  Done in {elapsed:.1f}s ({speed:.1f} MB/s) md5={local_md5[:12]}...")


def upload_checkpoint(s3, version: str, best_only: bool = False):
    """Upload checkpoint directory to R2."""
    ckpt_dir = CHECKPOINTS_DIR / version
    if not ckpt_dir.exists():
        # Try glob
        matches = sorted(CHECKPOINTS_DIR.glob(f"{version}*"))
        if not matches:
            sys.exit(f"No checkpoint directory matching: {version}")
        ckpt_dir = matches[-1]

    pt_files = sorted(ckpt_dir.glob("*.pt"))
    if not pt_files:
        sys.exit(f"No .pt files in {ckpt_dir}")

    if best_only:
        # Prefer best_final.pt > best.pt
        best = ckpt_dir / "best_final.pt"
        if not best.exists():
            best = ckpt_dir / "best.pt"
        if not best.exists():
            sys.exit(f"No best.pt in {ckpt_dir}")
        pt_files = [best]

    print(f"Checkpoint: {ckpt_dir.name} ({len(pt_files)} files)")
    metadata = {"version": ckpt_dir.name, "source": "local-mac"}

    manifest = {
        "version": ckpt_dir.name,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "files": [],
    }

    for f in pt_files:
        key = f"checkpoints/{ckpt_dir.name}/{f.name}"
        upload_file(s3, f, key, metadata)
        manifest["files"].append({
            "name": f.name,
            "size_mb": round(f.stat().st_size / 1024 / 1024, 1),
            "md5": md5sum(f),
            "r2_key": key,
        })

    # Upload manifest
    manifest_path = ckpt_dir / "_r2_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    manifest_key = f"checkpoints/{ckpt_dir.name}/_manifest.json"
    s3.put_object(Bucket=BUCKET, Key=manifest_key, Body=json.dumps(manifest, indent=2))
    print(f"  Manifest -> r2://{BUCKET}/{manifest_key}")

    print(f"\nTotal: {sum(f.stat().st_size for f in pt_files) / 1024 / 1024 / 1024:.2f} GB uploaded")


def upload_corpus(s3, version: str):
    """Upload corpus files."""
    pattern = f"data/corpus_{version}*.txt"
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        sys.exit(f"No corpus matching {pattern}")
    for f in matches:
        key = f"corpus/{f.name}"
        upload_file(s3, f, key)


def list_r2(s3, prefix: str = ""):
    """List R2 bucket contents."""
    print(f"R2 bucket: {BUCKET}")
    paginator = s3.get_paginator("list_objects_v2")
    total_size = 0
    total_count = 0
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            size_mb = obj["Size"] / 1024 / 1024
            total_size += obj["Size"]
            total_count += 1
            modified = obj["LastModified"].strftime("%Y-%m-%d %H:%M")
            print(f"  {obj['Key']:60s} {size_mb:8.1f} MB  {modified}")
    print(f"\nTotal: {total_count} files, {total_size / 1024 / 1024 / 1024:.2f} GB")


def download_file(s3, r2_key: str, local_dir: str = "."):
    """Download a file from R2."""
    local_path = Path(local_dir) / Path(r2_key).name
    print(f"Downloading r2://{BUCKET}/{r2_key} -> {local_path}")
    from boto3.s3.transfer import TransferConfig
    config = TransferConfig(
        multipart_threshold=50 * 1024 * 1024,
        multipart_chunksize=50 * 1024 * 1024,
        max_concurrency=4,
    )
    s3.download_file(BUCKET, r2_key, str(local_path), Config=config)
    print(f"  Done: {local_path} ({local_path.stat().st_size / 1024 / 1024:.1f} MB)")


def prune_checkpoints(s3, keep: int = 3):
    """Keep only the latest N checkpoint versions in R2."""
    paginator = s3.get_paginator("list_objects_v2")
    versions = set()
    for page in paginator.paginate(Bucket=BUCKET, Prefix="checkpoints/"):
        for obj in page.get("Contents", []):
            parts = obj["Key"].split("/")
            if len(parts) >= 2:
                versions.add(parts[1])

    versions = sorted(versions)
    if len(versions) <= keep:
        print(f"Only {len(versions)} versions, keeping all.")
        return

    to_delete = versions[:-keep]
    print(f"Pruning {len(to_delete)} old versions, keeping latest {keep}: {versions[-keep:]}")
    for v in to_delete:
        prefix = f"checkpoints/{v}/"
        for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
            objects = [{"Key": obj["Key"]} for obj in page.get("Contents", [])]
            if objects:
                s3.delete_objects(Bucket=BUCKET, Delete={"Objects": objects})
                print(f"  Deleted {len(objects)} files from {v}")


def main():
    ap = argparse.ArgumentParser(description="Anima R2 checkpoint manager")
    ap.add_argument("--checkpoint", help="Checkpoint version dir name, e.g. v14_128c_final")
    ap.add_argument("--best", action="store_true", help="Upload best.pt only")
    ap.add_argument("--corpus", help="Corpus version, e.g. v6")
    ap.add_argument("--list", action="store_true", help="List R2 contents")
    ap.add_argument("--prefix", default="", help="Prefix filter for --list")
    ap.add_argument("--download", help="R2 key to download")
    ap.add_argument("--prune", action="store_true", help="Prune old checkpoint versions")
    ap.add_argument("--keep", type=int, default=3, help="Versions to keep (with --prune)")
    args = ap.parse_args()

    if not any([args.checkpoint, args.corpus, args.list, args.download, args.prune]):
        ap.error("Specify --checkpoint, --corpus, --list, --download, or --prune")

    s3 = get_s3()

    if args.list:
        list_r2(s3, prefix=args.prefix)
    if args.download:
        download_file(s3, args.download)
    if args.checkpoint:
        upload_checkpoint(s3, args.checkpoint, best_only=args.best)
    if args.corpus:
        upload_corpus(s3, args.corpus)
    if args.prune:
        prune_checkpoints(s3, keep=args.keep)


if __name__ == "__main__":
    main()

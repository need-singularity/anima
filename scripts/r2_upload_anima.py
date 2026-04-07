#!/usr/bin/env python3
"""R2 Upload — Upload checkpoints to Cloudflare R2 (anima-models bucket)

Usage:
  python3 scripts/r2_upload.py --checkpoint v3_274M          # Upload best.pt + final.pt
  python3 scripts/r2_upload.py --file best.pt --key checkpoints/v3_274M/best.pt
  python3 scripts/r2_upload.py --list --prefix checkpoints/
  python3 scripts/r2_upload.py --download checkpoints/v3_274M/best.pt --output ./best.pt
  python3 scripts/r2_upload.py --prune --keep 3

R2 credentials: anima/.env or anima/.local/.env
  ANIMA_R2_ENDPOINT, ANIMA_R2_ACCESS_KEY, ANIMA_R2_SECRET_KEY
Bucket: anima-models
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path

# Load .env
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent  # anima/
for env_path in [PROJECT_DIR / ".env", PROJECT_DIR / ".local" / ".env"]:
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

ENDPOINT = os.environ.get("ANIMA_R2_ENDPOINT")
ACCESS_KEY = os.environ.get("ANIMA_R2_ACCESS_KEY")
SECRET_KEY = os.environ.get("ANIMA_R2_SECRET_KEY")
BUCKET = os.environ.get("ANIMA_R2_MODELS_BUCKET", "anima-models")


def get_client():
    import boto3
    from botocore.config import Config
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        config=Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "adaptive"}),
        region_name="auto",
    )


def md5_file(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(n) < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def upload_file(client, local_path: str, key: str):
    """Upload a single file to R2."""
    size = os.path.getsize(local_path)
    md5 = md5_file(local_path)
    print(f"  Uploading {local_path} ({human_size(size)}, md5={md5[:12]}...)")
    print(f"    -> r2://{BUCKET}/{key}")
    client.upload_file(
        Filename=local_path,
        Bucket=BUCKET,
        Key=key,
        ExtraArgs={"Metadata": {"md5": md5, "size": str(size), "uploaded": datetime.utcnow().isoformat()}},
    )
    print(f"    Done.")
    return {"key": key, "size": size, "md5": md5}


def upload_checkpoint(version: str, checkpoint_dir: str = None):
    """Upload best.pt and final.pt for a training version."""
    client = get_client()
    ckpt_dir = checkpoint_dir or str(PROJECT_DIR / "checkpoints" / version)

    if not os.path.isdir(ckpt_dir):
        print(f"ERROR: Checkpoint directory not found: {ckpt_dir}")
        sys.exit(1)

    results = []
    for fname in ["best.pt", "final.pt", "best_final.pt", "step_200000.pt"]:
        fpath = os.path.join(ckpt_dir, fname)
        if os.path.exists(fpath):
            key = f"checkpoints/{version}/{fname}"
            r = upload_file(client, fpath, key)
            results.append(r)

    if not results:
        print(f"WARNING: No checkpoint files found in {ckpt_dir}")
        print(f"  Looked for: best.pt, final.pt, best_final.pt, step_200000.pt")
        sys.exit(1)

    print(f"\n=== Upload Complete ===")
    for r in results:
        print(f"  {r['key']}  ({human_size(r['size'])})")
    return results


def list_objects(prefix: str = ""):
    """List objects in R2 bucket."""
    client = get_client()
    paginator = client.get_paginator("list_objects_v2")
    print(f"=== r2://{BUCKET}/{prefix} ===")
    total = 0
    for page in paginator.paginate(Bucket=BUCKET, Prefix=prefix):
        for obj in page.get("Contents", []):
            size = human_size(obj["Size"])
            mod = obj["LastModified"].strftime("%Y-%m-%d %H:%M")
            print(f"  {obj['Key']:60s}  {size:>10s}  {mod}")
            total += 1
    if total == 0:
        print("  (empty)")
    print(f"\nTotal: {total} objects")


def download_object(key: str, output: str):
    """Download a single object from R2."""
    client = get_client()
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    print(f"Downloading r2://{BUCKET}/{key} -> {output}")
    client.download_file(Bucket=BUCKET, Key=key, Filename=output)
    size = os.path.getsize(output)
    print(f"  Done ({human_size(size)})")


def prune_checkpoints(keep: int = 3):
    """Prune old checkpoint versions, keeping the latest N."""
    client = get_client()
    paginator = client.get_paginator("list_objects_v2")
    versions = {}
    for page in paginator.paginate(Bucket=BUCKET, Prefix="checkpoints/"):
        for obj in page.get("Contents", []):
            parts = obj["Key"].split("/")
            if len(parts) >= 2:
                ver = parts[1]
                if ver not in versions:
                    versions[ver] = []
                versions[ver].append(obj)

    sorted_versions = sorted(versions.keys(), key=lambda v: max(o["LastModified"] for o in versions[v]), reverse=True)

    if len(sorted_versions) <= keep:
        print(f"Only {len(sorted_versions)} versions, keeping all (threshold: {keep})")
        return

    to_delete = sorted_versions[keep:]
    print(f"Pruning {len(to_delete)} old versions (keeping {keep} newest):")
    for ver in to_delete:
        for obj in versions[ver]:
            print(f"  Deleting {obj['Key']}")
            client.delete_object(Bucket=BUCKET, Key=obj["Key"])
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="R2 checkpoint upload/manage")
    parser.add_argument("--checkpoint", "-c", help="Upload checkpoint version (e.g. v3_274M)")
    parser.add_argument("--dir", help="Checkpoint directory (default: checkpoints/<version>)")
    parser.add_argument("--file", "-f", help="Upload single file")
    parser.add_argument("--key", "-k", help="R2 key for single file upload")
    parser.add_argument("--list", "-l", action="store_true", help="List objects")
    parser.add_argument("--prefix", "-p", default="", help="Prefix for list")
    parser.add_argument("--download", "-d", help="Download object by key")
    parser.add_argument("--output", "-o", help="Output path for download")
    parser.add_argument("--prune", action="store_true", help="Prune old versions")
    parser.add_argument("--keep", type=int, default=3, help="Versions to keep (default: 3)")
    args = parser.parse_args()

    if not all([ENDPOINT, ACCESS_KEY, SECRET_KEY]):
        print("ERROR: R2 credentials not set.")
        print("  Set ANIMA_R2_ENDPOINT, ANIMA_R2_ACCESS_KEY, ANIMA_R2_SECRET_KEY")
        print("  Or create anima/.env or anima/.local/.env")
        sys.exit(1)

    if args.checkpoint:
        upload_checkpoint(args.checkpoint, args.dir)
    elif args.file:
        if not args.key:
            print("ERROR: --key required with --file")
            sys.exit(1)
        client = get_client()
        upload_file(client, args.file, args.key)
    elif args.list:
        list_objects(args.prefix)
    elif args.download:
        output = args.output or os.path.basename(args.download)
        download_object(args.download, output)
    elif args.prune:
        prune_checkpoints(args.keep)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

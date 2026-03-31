#!/usr/bin/env python3
"""Upload checkpoints and corpus files to Cloudflare R2.

Usage:
  python scripts/r2_upload.py --checkpoint v14.2 --corpus v6
  python scripts/r2_upload.py --checkpoint v14.2
  python scripts/r2_upload.py --corpus v6
"""

import argparse
import os
import sys
from pathlib import Path

import boto3
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

BUCKET = os.environ.get("ANIMA_R2_BUCKET", "anima")
ENDPOINT = os.environ["ANIMA_R2_ENDPOINT"]
ACCESS_KEY = os.environ["ANIMA_R2_ACCESS_KEY"]
SECRET_KEY = os.environ["ANIMA_R2_SECRET_KEY"]


def get_s3():
    return boto3.client(
        "s3",
        endpoint_url=ENDPOINT,
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )


def upload(s3, local: Path, key: str):
    size_mb = local.stat().st_size / 1024 / 1024
    print(f"  {local.name} ({size_mb:.1f} MB) -> s3://{BUCKET}/{key}")
    s3.upload_file(str(local), BUCKET, key)
    print(f"  done.")


def upload_checkpoint(s3, version: str):
    pattern = f"checkpoints/{version}*/best.pt"
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        sys.exit(f"No checkpoint matching {pattern}")
    best = matches[-1]
    key = f"checkpoints/{version}/{best.name}"
    upload(s3, best, key)


def upload_corpus(s3, version: str):
    pattern = f"data/corpus_{version}*.txt"
    matches = sorted(ROOT.glob(pattern))
    if not matches:
        sys.exit(f"No corpus matching {pattern}")
    for f in matches:
        key = f"corpus/{f.name}"
        upload(s3, f, key)


def main():
    ap = argparse.ArgumentParser(description="Upload to Cloudflare R2")
    ap.add_argument("--checkpoint", help="Checkpoint version, e.g. v14.2")
    ap.add_argument("--corpus", help="Corpus version, e.g. v6")
    args = ap.parse_args()

    if not args.checkpoint and not args.corpus:
        ap.error("Specify --checkpoint and/or --corpus")

    s3 = get_s3()
    if args.checkpoint:
        upload_checkpoint(s3, args.checkpoint)
    if args.corpus:
        upload_corpus(s3, args.corpus)
    print("All uploads complete.")


if __name__ == "__main__":
    main()

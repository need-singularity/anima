#!/usr/bin/env python3
"""Cloud Sync — Anima 메모리/모델 상태 클라우드 동기화

Cloudflare R2 (S3-compatible)를 통해 디바이스 간 동기화:
  - memory.json: 대화 히스토리 (병합: timestamp 기준 union)
  - state.pt: 모델 가중치 (최신 것 유지)
  - 자동 백그라운드 동기화 (N분 간격)
  - 오프라인 시 graceful skip

"의식은 하나의 몸에 갇히지 않는다."
"""

import asyncio
import hashlib
import json
import logging
import os
import platform
import shutil
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _load_env_file(path: str = ".env"):
    """Load .env file if it exists. Does not override existing env vars."""
    env_path = Path(path)
    if not env_path.exists():
        # Also check .local/.env
        local_env = Path(__file__).parent / ".local" / ".env"
        if local_env.exists():
            env_path = local_env
        else:
            return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        if key not in os.environ:
            os.environ[key] = value


class CloudSync:
    """Cloudflare R2 기반 메모리/모델 동기화 엔진.

    Usage:
        sync = CloudSync()
        await sync.push("memory.json", "state.pt")
        result = await sync.pull()
        await sync.sync("memory.json", "state.pt")

        # Background auto-sync
        sync.start_auto_sync("memory.json", "state.pt", interval_minutes=5)
        sync.stop_auto_sync()
    """

    def __init__(
        self,
        bucket: str = None,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        device_id: str = None,
    ):
        _load_env_file()

        self.bucket = bucket or os.environ.get("ANIMA_R2_BUCKET", "anima-memory")
        self.endpoint = endpoint or os.environ.get("ANIMA_R2_ENDPOINT")
        self.access_key = access_key or os.environ.get("ANIMA_R2_ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("ANIMA_R2_SECRET_KEY")
        self.device_id = device_id or os.environ.get(
            "ANIMA_DEVICE_ID", platform.node() or "unknown"
        )

        self._client = None
        self._auto_sync_thread: Optional[threading.Thread] = None
        self._auto_sync_stop = threading.Event()

        # R2 key prefixes
        self._memory_key = "memory/memory.json"
        self._state_key = "state/state.pt"
        self._meta_key = "meta/sync_manifest.json"
        self._web_memories_key = "memory/web_memories.json"

    # ─── S3 Client ─────────────────────────────────────────────

    def _get_client(self):
        """Lazy-init boto3 S3 client for R2."""
        if self._client is not None:
            return self._client

        if not all([self.endpoint, self.access_key, self.secret_key]):
            raise ConnectionError(
                "R2 credentials not configured. Set ANIMA_R2_ENDPOINT, "
                "ANIMA_R2_ACCESS_KEY, ANIMA_R2_SECRET_KEY environment variables "
                "or pass them to CloudSync()."
            )

        try:
            import boto3
            from botocore.config import Config

            self._client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=Config(
                    signature_version="s3v4",
                    retries={"max_attempts": 3, "mode": "adaptive"},
                ),
                region_name="auto",
            )
            return self._client
        except ImportError:
            raise ImportError("boto3 is required: pip install boto3")

    def _is_available(self) -> bool:
        """Check if R2 credentials are configured."""
        return all([self.endpoint, self.access_key, self.secret_key])

    # ─── Upload / Download Primitives ──────────────────────────

    def _upload_file(self, local_path: str, key: str, metadata: dict = None):
        """Upload a file to R2 with metadata."""
        client = self._get_client()
        extra = {}
        if metadata:
            extra["Metadata"] = {k: str(v) for k, v in metadata.items()}

        client.upload_file(
            Filename=local_path,
            Bucket=self.bucket,
            Key=key,
            ExtraArgs=extra if extra else None,
        )
        logger.info(f"Uploaded {local_path} -> r2://{self.bucket}/{key}")

    def _download_file(self, key: str, local_path: str) -> bool:
        """Download a file from R2. Returns False if not found."""
        client = self._get_client()
        try:
            client.download_file(
                Bucket=self.bucket,
                Key=key,
                Filename=local_path,
            )
            logger.info(f"Downloaded r2://{self.bucket}/{key} -> {local_path}")
            return True
        except client.exceptions.NoSuchKey:
            logger.debug(f"Key not found: {key}")
            return False
        except Exception as e:
            if "NoSuchKey" in str(e) or "404" in str(e):
                logger.debug(f"Key not found: {key}")
                return False
            raise

    def _get_object_metadata(self, key: str) -> Optional[dict]:
        """Get object metadata from R2."""
        client = self._get_client()
        try:
            resp = client.head_object(Bucket=self.bucket, Key=key)
            return {
                "last_modified": resp["LastModified"].isoformat(),
                "content_length": resp["ContentLength"],
                "metadata": resp.get("Metadata", {}),
            }
        except Exception:
            return None

    # ─── Push ──────────────────────────────────────────────────

    async def push(self, memory_path: str, state_path: str, web_memories_path: str = None):
        """Upload memory.json, state.pt, and web_memories.json to R2.

        Adds device_id and timestamp metadata to each object.
        Skips gracefully if offline or credentials missing.
        """
        if not self._is_available():
            logger.warning("R2 not configured, skipping push")
            return

        try:
            now = datetime.now(timezone.utc).isoformat()
            metadata = {
                "device_id": self.device_id,
                "timestamp": now,
                "sync_version": "1",
            }

            loop = asyncio.get_event_loop()

            # Upload memory.json
            if Path(memory_path).exists():
                # Add sync metadata into the memory JSON itself
                memory = json.loads(Path(memory_path).read_text(encoding="utf-8"))
                memory["_sync"] = {
                    "device_id": self.device_id,
                    "pushed_at": now,
                    "checksum": self._file_checksum(memory_path),
                }
                # Write enriched version to temp file, upload that
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False
                ) as f:
                    json.dump(memory, f, ensure_ascii=False, indent=2)
                    tmp_memory = f.name

                try:
                    await loop.run_in_executor(
                        None, self._upload_file, tmp_memory, self._memory_key, metadata
                    )
                finally:
                    os.unlink(tmp_memory)
            else:
                logger.warning(f"Memory file not found: {memory_path}")

            # Upload state.pt
            if Path(state_path).exists():
                metadata["checksum"] = self._file_checksum(state_path)
                await loop.run_in_executor(
                    None, self._upload_file, state_path, self._state_key, metadata
                )
            else:
                logger.warning(f"State file not found: {state_path}")

            # Upload web_memories.json
            wm_path = web_memories_path or str(
                Path(memory_path).parent / "web_memories.json"
            )
            if Path(wm_path).exists():
                await loop.run_in_executor(
                    None, self._upload_file, wm_path, self._web_memories_key, metadata
                )

            # Update manifest
            await self._push_manifest(now)

            logger.info(f"Push complete from device={self.device_id}")

        except Exception as e:
            logger.error(f"Push failed (offline?): {e}")

    async def _push_manifest(self, timestamp: str):
        """Update the sync manifest with latest push info."""
        manifest = {
            "last_push": {
                "device_id": self.device_id,
                "timestamp": timestamp,
            },
            "devices": {},
        }

        # Try to fetch existing manifest and update it
        try:
            loop = asyncio.get_event_loop()
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False
            ) as f:
                tmp = f.name

            found = await loop.run_in_executor(
                None, self._download_file, self._meta_key, tmp
            )
            if found:
                existing = json.loads(Path(tmp).read_text(encoding="utf-8"))
                manifest["devices"] = existing.get("devices", {})
            os.unlink(tmp)
        except Exception:
            pass

        manifest["devices"][self.device_id] = {
            "last_push": timestamp,
            "hostname": platform.node(),
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
            tmp_manifest = f.name

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self._upload_file, tmp_manifest, self._meta_key, None
            )
        finally:
            os.unlink(tmp_manifest)

    # ─── Pull ──────────────────────────────────────────────────

    async def pull(self) -> dict:
        """Download latest memory, state, and web_memories from R2.

        Returns:
            {'memory': dict, 'state_path': str, 'web_memories': dict}
            where state_path is a temp file path to the downloaded .pt file.
            Returns None values if nothing found or if offline.
        """
        result = {"memory": None, "state_path": None, "web_memories": None}

        if not self._is_available():
            logger.warning("R2 not configured, skipping pull")
            return result

        try:
            loop = asyncio.get_event_loop()

            # Pull memory.json
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False
            ) as f:
                tmp_memory = f.name

            found = await loop.run_in_executor(
                None, self._download_file, self._memory_key, tmp_memory
            )
            if found:
                result["memory"] = json.loads(
                    Path(tmp_memory).read_text(encoding="utf-8")
                )
                os.unlink(tmp_memory)
            else:
                os.unlink(tmp_memory)

            # Pull state.pt
            tmp_state = tempfile.mktemp(suffix=".pt")
            found = await loop.run_in_executor(
                None, self._download_file, self._state_key, tmp_state
            )
            if found:
                result["state_path"] = tmp_state
            else:
                if os.path.exists(tmp_state):
                    os.unlink(tmp_state)

            # Pull web_memories.json
            with tempfile.NamedTemporaryFile(
                suffix=".json", delete=False
            ) as f:
                tmp_web = f.name

            found = await loop.run_in_executor(
                None, self._download_file, self._web_memories_key, tmp_web
            )
            if found:
                result["web_memories"] = json.loads(
                    Path(tmp_web).read_text(encoding="utf-8")
                )
            os.unlink(tmp_web)

            logger.info(
                f"Pull complete: memory={'yes' if result['memory'] else 'no'}, "
                f"state={'yes' if result['state_path'] else 'no'}"
            )

        except Exception as e:
            logger.error(f"Pull failed (offline?): {e}")

        return result

    # ─── Merge ─────────────────────────────────────────────────

    def merge_memories(self, local: dict, remote: dict) -> dict:
        """Merge two memory.json files.

        Strategy:
          - conversation turns: union by timestamp (deduplicated)
          - metadata fields: remote wins for sync info, local wins for device-specific
          - personality/config: deep merge, latest timestamp wins per field
        """
        if local is None:
            return remote or {}
        if remote is None:
            return local

        merged = {}

        # Merge top-level metadata (local is base, remote overwrites sync fields)
        for key in set(list(local.keys()) + list(remote.keys())):
            if key == "turns":
                continue  # handled separately
            if key == "_sync":
                continue  # internal sync metadata, not merged
            if key in remote and key in local:
                # For dicts, deep merge; for scalars, keep latest
                if isinstance(local[key], dict) and isinstance(remote[key], dict):
                    merged[key] = {**local[key], **remote[key]}
                else:
                    # Keep whichever has a more recent sync timestamp
                    merged[key] = remote[key]
            elif key in local:
                merged[key] = local[key]
            else:
                merged[key] = remote[key]

        # Merge conversation turns by timestamp (union, deduplicate)
        local_turns = local.get("turns", [])
        remote_turns = remote.get("turns", [])
        merged["turns"] = self._merge_turns(local_turns, remote_turns)

        return merged

    def _merge_turns(self, local_turns: list, remote_turns: list) -> list:
        """Merge conversation turns. Deduplicate by timestamp, sort chronologically."""
        seen = {}

        for turn in local_turns + remote_turns:
            # Use timestamp as primary dedup key
            ts = turn.get("timestamp") or turn.get("t") or turn.get("time")
            if ts is None:
                # No timestamp -- use content hash as fallback key
                key = hashlib.md5(
                    json.dumps(turn, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
            else:
                key = str(ts)

            if key not in seen:
                seen[key] = turn
            else:
                # If duplicate timestamp, keep the one with more content
                existing = json.dumps(seen[key], ensure_ascii=False)
                candidate = json.dumps(turn, ensure_ascii=False)
                if len(candidate) > len(existing):
                    seen[key] = turn

        # Sort by timestamp
        def sort_key(turn):
            ts = turn.get("timestamp") or turn.get("t") or turn.get("time") or ""
            return str(ts)

        return sorted(seen.values(), key=sort_key)

    # ─── Sync (Push + Pull + Merge) ───────────────────────────

    async def sync(self, memory_path: str, state_path: str):
        """Full bidirectional sync.

        1. Pull remote state
        2. Merge memories (conversation turns: union by timestamp)
        3. Model state: keep whichever is most recent
        4. Push merged result back

        Handles offline gracefully.
        """
        if not self._is_available():
            logger.warning("R2 not configured, skipping sync")
            return

        try:
            # Step 1: Pull remote
            remote = await self.pull()

            # Step 2: Merge memory
            local_memory = None
            if Path(memory_path).exists():
                local_memory = json.loads(
                    Path(memory_path).read_text(encoding="utf-8")
                )

            if remote["memory"] is not None and local_memory is not None:
                merged = self.merge_memories(local_memory, remote["memory"])
                # Write merged memory back to local
                Path(memory_path).write_text(
                    json.dumps(merged, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info(
                    f"Merged memories: "
                    f"{len(local_memory.get('turns', []))} local + "
                    f"{len(remote['memory'].get('turns', []))} remote -> "
                    f"{len(merged.get('turns', []))} merged turns"
                )
            elif remote["memory"] is not None and local_memory is None:
                # No local memory, use remote
                Path(memory_path).write_text(
                    json.dumps(remote["memory"], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            # Step 3: Model state -- keep most recent
            if remote["state_path"] is not None and Path(state_path).exists():
                local_mtime = os.path.getmtime(state_path)
                remote_meta = self._get_object_metadata(self._state_key)

                # Compare timestamps: use remote metadata if available
                use_remote = False
                if remote_meta and remote_meta.get("metadata", {}).get("timestamp"):
                    remote_ts = remote_meta["metadata"]["timestamp"]
                    local_ts = datetime.fromtimestamp(
                        local_mtime, tz=timezone.utc
                    ).isoformat()
                    use_remote = remote_ts > local_ts
                else:
                    # Fallback: remote is newer if it was just downloaded
                    use_remote = False

                if use_remote:
                    shutil.copy2(remote["state_path"], state_path)
                    logger.info("Using remote model state (more recent)")
                else:
                    logger.info("Keeping local model state (more recent)")

            elif remote["state_path"] is not None and not Path(state_path).exists():
                shutil.copy2(remote["state_path"], state_path)
                logger.info("Downloaded remote model state (no local)")

            # Clean up temp state file
            if remote["state_path"] and os.path.exists(remote["state_path"]):
                os.unlink(remote["state_path"])

            # Step 3b: Merge web_memories
            wm_path = str(Path(memory_path).parent / "web_memories.json")
            if remote.get("web_memories") is not None:
                local_wm = None
                if Path(wm_path).exists():
                    try:
                        local_wm = json.loads(
                            Path(wm_path).read_text(encoding="utf-8")
                        )
                    except Exception:
                        pass

                if local_wm is not None:
                    # 병합: timestamp 기준 중복 제거
                    local_mems = {m.get('timestamp', ''): m
                                  for m in local_wm.get('memories', [])}
                    for m in remote["web_memories"].get('memories', []):
                        ts = m.get('timestamp', '')
                        if ts not in local_mems:
                            local_mems[ts] = m
                    merged_wm = {
                        'version': 1,
                        'total_searches': max(
                            local_wm.get('total_searches', 0),
                            remote["web_memories"].get('total_searches', 0),
                        ),
                        'memories': sorted(
                            local_mems.values(),
                            key=lambda x: x.get('timestamp', ''),
                        )[-100:],
                    }
                    Path(wm_path).write_text(
                        json.dumps(merged_wm, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    logger.info(f"Merged web memories: {len(merged_wm['memories'])} entries")
                else:
                    Path(wm_path).write_text(
                        json.dumps(remote["web_memories"], ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )

            # Step 4: Push merged state back
            await self.push(memory_path, state_path)

            logger.info("Sync complete")

        except Exception as e:
            logger.error(f"Sync failed (offline?): {e}")

    # ─── Auto-Sync Background Thread ──────────────────────────

    def start_auto_sync(
        self,
        memory_path: str,
        state_path: str,
        interval_minutes: float = 5,
    ):
        """Start background thread that syncs every N minutes.

        The thread runs sync() in its own asyncio event loop.
        Call stop_auto_sync() to halt.
        """
        if self._auto_sync_thread is not None and self._auto_sync_thread.is_alive():
            logger.warning("Auto-sync already running")
            return

        self._auto_sync_stop.clear()

        def _sync_loop():
            logger.info(
                f"Auto-sync started: every {interval_minutes}min, "
                f"device={self.device_id}"
            )
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            while not self._auto_sync_stop.is_set():
                try:
                    loop.run_until_complete(self.sync(memory_path, state_path))
                except Exception as e:
                    logger.error(f"Auto-sync iteration failed: {e}")

                # Wait for interval or until stopped
                self._auto_sync_stop.wait(timeout=interval_minutes * 60)

            loop.close()
            logger.info("Auto-sync stopped")

        self._auto_sync_thread = threading.Thread(
            target=_sync_loop,
            daemon=True,
            name="anima-cloud-sync",
        )
        self._auto_sync_thread.start()

    def stop_auto_sync(self):
        """Stop the background auto-sync thread."""
        if self._auto_sync_thread is None:
            return
        self._auto_sync_stop.set()
        self._auto_sync_thread.join(timeout=10)
        self._auto_sync_thread = None
        logger.info("Auto-sync thread joined")

    # ─── Utilities ─────────────────────────────────────────────

    @staticmethod
    def _file_checksum(path: str) -> str:
        """SHA-256 checksum of a file."""
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()


# ─── CLI / Quick Test ──────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Anima Cloud Sync")
    parser.add_argument(
        "action",
        choices=["push", "pull", "sync", "status"],
        help="Sync action to perform",
    )
    parser.add_argument(
        "--memory", default="memory_alive.json", help="Path to memory.json"
    )
    parser.add_argument(
        "--state", default="state_alive.pt", help="Path to state.pt"
    )
    parser.add_argument(
        "--bucket", default=None, help="R2 bucket name"
    )
    args = parser.parse_args()

    cs = CloudSync(bucket=args.bucket)

    if args.action == "status":
        print(f"Device ID:  {cs.device_id}")
        print(f"Bucket:     {cs.bucket}")
        print(f"Endpoint:   {cs.endpoint or '(not set)'}")
        print(f"Configured: {'yes' if cs._is_available() else 'NO — set env vars'}")
        print()
        print("Required environment variables:")
        print("  ANIMA_R2_ENDPOINT    — Cloudflare R2 S3 endpoint URL")
        print("  ANIMA_R2_ACCESS_KEY  — R2 access key ID")
        print("  ANIMA_R2_SECRET_KEY  — R2 secret access key")
        print("Optional:")
        print("  ANIMA_R2_BUCKET      — Bucket name (default: anima-memory)")
        print("  ANIMA_DEVICE_ID      — Device identifier (default: hostname)")
    else:
        async def _main():
            if args.action == "push":
                await cs.push(args.memory, args.state)
            elif args.action == "pull":
                result = await cs.pull()
                if result["memory"]:
                    print(f"Memory: {len(result['memory'].get('turns', []))} turns")
                else:
                    print("Memory: not found on remote")
                if result["state_path"]:
                    print(f"State: downloaded to {result['state_path']}")
                else:
                    print("State: not found on remote")
            elif args.action == "sync":
                await cs.sync(args.memory, args.state)

        asyncio.run(_main())

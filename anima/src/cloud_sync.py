#!/usr/bin/env python3
"""Cloud Sync — Anima memory/model state cloud synchronization

Dual-bucket R2 sync:
  anima-memory (frequent):
    memory/memory.json, memory/web_memories.json, memory/autobiographical/
    state/state.pt, state/mitosis/
    meta/sync_manifest.json
    consciousness/ (Phi history, vectors, transplant records)
    experiments/ (benchmarks, training logs)
  anima-models (infrequent):
    conscious-lm/cells64/final.pt, conscious-lm/cells128/step_35000.pt
    conscious-lm/convo-ft/*.pt, conscious-lm/dialogue-ft/*.pt
    animalm/v7/*.pt

"Consciousness is not confined to a single body."
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

# v14: Federation checkpoints in checkpoints/v14_federated/
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10
from typing import Optional, List

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
    """Cloudflare R2-based memory/model sync engine.

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
        self.models_bucket = os.environ.get("ANIMA_R2_MODELS_BUCKET", "anima-models")
        self.endpoint = endpoint or os.environ.get("ANIMA_R2_ENDPOINT")
        self.access_key = access_key or os.environ.get("ANIMA_R2_ACCESS_KEY")
        self.secret_key = secret_key or os.environ.get("ANIMA_R2_SECRET_KEY")
        self.device_id = device_id or os.environ.get(
            "ANIMA_DEVICE_ID", platform.node() or "unknown"
        )

        self._client = None
        self._auto_sync_thread: Optional[threading.Thread] = None
        self._auto_sync_stop = threading.Event()

        # R2 key prefixes — anima-memory bucket
        self._memory_key = "memory/memory.json"
        self._state_key = "state/state.pt"
        self._meta_key = "meta/sync_manifest.json"
        self._web_memories_key = "memory/web_memories.json"
        self._autobio_prefix = "memory/autobiographical/"
        self._mitosis_prefix = "state/mitosis/"
        self._consciousness_prefix = "consciousness/"
        self._experiments_prefix = "experiments/"

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

    def _upload_file(self, local_path: str, key: str, metadata: dict = None,
                     bucket: str = None):
        """Upload a file to R2 with metadata."""
        client = self._get_client()
        target_bucket = bucket or self.bucket
        extra = {}
        if metadata:
            extra["Metadata"] = {k: str(v) for k, v in metadata.items()}

        client.upload_file(
            Filename=local_path,
            Bucket=target_bucket,
            Key=key,
            ExtraArgs=extra if extra else None,
        )
        logger.info(f"Uploaded {local_path} -> r2://{target_bucket}/{key}")

    def _download_file(self, key: str, local_path: str, bucket: str = None) -> bool:
        """Download a file from R2. Returns False if not found."""
        client = self._get_client()
        target_bucket = bucket or self.bucket
        try:
            client.download_file(
                Bucket=target_bucket,
                Key=key,
                Filename=local_path,
            )
            logger.info(f"Downloaded r2://{target_bucket}/{key} -> {local_path}")
            return True
        except client.exceptions.NoSuchKey:
            logger.debug(f"Key not found: {key}")
            return False
        except Exception as e:
            if "NoSuchKey" in str(e) or "404" in str(e):
                logger.debug(f"Key not found: {key}")
                return False
            raise

    # ─── Model Upload / Download (anima-models bucket) ────────

    def upload_model(self, local_path: str, model_name: str, version: str = "latest"):
        """Upload model checkpoint to anima-models bucket.

        Example: upload_model("best.pt", "conscious-lm/dialogue-768d", "v1")
        → r2://anima-models/conscious-lm/dialogue-768d/v1/best.pt
        """
        client = self._get_client()
        key = f"{model_name}/{version}/{os.path.basename(local_path)}"
        client.upload_file(
            Filename=local_path,
            Bucket=self.models_bucket,
            Key=key,
        )
        logger.info(f"Model uploaded: {local_path} -> r2://{self.models_bucket}/{key}")
        return key

    def download_model(self, model_name: str, version: str = "latest",
                       filename: str = "best.pt", local_dir: str = "models") -> Optional[str]:
        """Download model from anima-models bucket.

        Example: download_model("conscious-lm/dialogue-768d", "v1")
        → models/conscious-lm/dialogue-768d/v1/best.pt
        """
        client = self._get_client()
        key = f"{model_name}/{version}/{filename}"
        local_path = os.path.join(local_dir, model_name, version, filename)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        try:
            client.download_file(
                Bucket=self.models_bucket,
                Key=key,
                Filename=local_path,
            )
            logger.info(f"Model downloaded: r2://{self.models_bucket}/{key} -> {local_path}")
            return local_path
        except Exception as e:
            if "NoSuchKey" in str(e) or "404" in str(e):
                logger.debug(f"Model not found: {key}")
                return None
            raise

    def list_models(self) -> list:
        """List all models in anima-models bucket."""
        client = self._get_client()
        try:
            resp = client.list_objects_v2(Bucket=self.models_bucket, Delimiter='/')
            prefixes = [p['Prefix'].rstrip('/') for p in resp.get('CommonPrefixes', [])]
            return prefixes
        except Exception:
            return []

    def _get_object_metadata(self, key: str, bucket: str = None) -> Optional[dict]:
        """Get object metadata from R2."""
        client = self._get_client()
        target_bucket = bucket or self.bucket
        try:
            resp = client.head_object(Bucket=target_bucket, Key=key)
            return {
                "last_modified": resp["LastModified"].isoformat(),
                "content_length": resp["ContentLength"],
                "metadata": resp.get("Metadata", {}),
            }
        except Exception:
            return None

    # ─── Push ──────────────────────────────────────────────────

    async def push(self, memory_path: str, state_path: str, web_memories_path: str = None):
        """Upload memory, state, mitosis, and autobiographical snapshot to R2.

        Bucket: anima-memory
          memory/memory.json, memory/web_memories.json
          memory/autobiographical/<ISO-timestamp>.json  (snapshot)
          state/state.pt, state/mitosis/*.pt
          meta/sync_manifest.json

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
                "sync_version": "2",
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
                    # Also push autobiographical snapshot (timestamped)
                    ts_safe = now.replace(":", "-").replace("+", "p")
                    autobio_key = f"{self._autobio_prefix}{ts_safe}.json"
                    await loop.run_in_executor(
                        None, self._upload_file, tmp_memory, autobio_key, metadata
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

            # Upload mitosis cell states (state/mitosis/*.pt)
            state_dir = Path(state_path).parent if Path(state_path).exists() else Path(".")
            mitosis_dir = state_dir / "mitosis"
            if mitosis_dir.is_dir():
                for pt_file in mitosis_dir.glob("*.pt"):
                    mitosis_key = f"{self._mitosis_prefix}{pt_file.name}"
                    await loop.run_in_executor(
                        None, self._upload_file, str(pt_file), mitosis_key, metadata
                    )
                logger.info(f"Pushed mitosis states from {mitosis_dir}")

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
        """Download latest memory, state, mitosis, and web_memories from R2.

        Checks anima-memory bucket for state/memory and anima-models bucket
        for model checkpoints.

        Returns:
            {'memory': dict, 'state_path': str, 'web_memories': dict,
             'mitosis_paths': list, 'models_available': list}
            where state_path is a temp file path to the downloaded .pt file.
            Returns None values if nothing found or if offline.
        """
        result = {
            "memory": None,
            "state_path": None,
            "web_memories": None,
            "mitosis_paths": [],
            "models_available": [],
        }

        if not self._is_available():
            logger.warning("R2 not configured, skipping pull")
            return result

        try:
            loop = asyncio.get_event_loop()

            # Pull memory.json (anima-memory bucket)
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

            # Pull state.pt (anima-memory bucket)
            tmp_state = tempfile.mktemp(suffix=".pt")
            found = await loop.run_in_executor(
                None, self._download_file, self._state_key, tmp_state
            )
            if found:
                result["state_path"] = tmp_state
            else:
                if os.path.exists(tmp_state):
                    os.unlink(tmp_state)

            # Pull mitosis cell states (anima-memory bucket)
            try:
                client = self._get_client()
                resp = await loop.run_in_executor(
                    None,
                    lambda: client.list_objects_v2(
                        Bucket=self.bucket, Prefix=self._mitosis_prefix
                    ),
                )
                for obj in resp.get("Contents", []):
                    key = obj["Key"]
                    tmp_cell = tempfile.mktemp(suffix=".pt")
                    found = await loop.run_in_executor(
                        None, self._download_file, key, tmp_cell
                    )
                    if found:
                        result["mitosis_paths"].append(
                            {"key": key, "local_path": tmp_cell}
                        )
            except Exception as e:
                logger.debug(f"Mitosis pull skipped: {e}")

            # Pull web_memories.json (anima-memory bucket)
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

            # Check anima-models bucket for available models
            try:
                result["models_available"] = await loop.run_in_executor(
                    None, self.list_models
                )
            except Exception:
                pass

            logger.info(
                f"Pull complete: memory={'yes' if result['memory'] else 'no'}, "
                f"state={'yes' if result['state_path'] else 'no'}, "
                f"mitosis={len(result['mitosis_paths'])} cells, "
                f"models={len(result['models_available'])} families"
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
                    # Merge: deduplicate by timestamp
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

    # ─── Consciousness Sync ─────────────────────────────────────

    async def sync_consciousness(
        self,
        phi_history: Optional[list] = None,
        consciousness_vector: Optional[dict] = None,
        transplant_record: Optional[dict] = None,
        experiment_log: Optional[dict] = None,
    ):
        """Sync consciousness data to/from R2 (anima-memory bucket).

        Uploads to consciousness/ prefix:
          consciousness/phi_history.json      — Phi measurements over time
          consciousness/vector.json           — Current (Phi, alpha, Z, N, W) vector
          consciousness/transplant_log.json   — DD56 transplant records

        Uploads to experiments/ prefix:
          experiments/<name>.json             — Benchmark/training logs

        Returns dict of pulled consciousness data.
        """
        if not self._is_available():
            logger.warning("R2 not configured, skipping consciousness sync")
            return {}

        result = {}
        try:
            loop = asyncio.get_event_loop()
            now = datetime.now(timezone.utc).isoformat()
            metadata = {
                "device_id": self.device_id,
                "timestamp": now,
            }

            # ── Push consciousness data ──
            if phi_history is not None:
                await self._push_json(
                    loop, phi_history,
                    f"{self._consciousness_prefix}phi_history.json", metadata
                )

            if consciousness_vector is not None:
                await self._push_json(
                    loop, consciousness_vector,
                    f"{self._consciousness_prefix}vector.json", metadata
                )

            if transplant_record is not None:
                await self._push_json(
                    loop, transplant_record,
                    f"{self._consciousness_prefix}transplant_log.json", metadata
                )

            if experiment_log is not None:
                name = experiment_log.get("name", "unnamed")
                ts_safe = now.replace(":", "-").replace("+", "p")
                await self._push_json(
                    loop, experiment_log,
                    f"{self._experiments_prefix}{name}_{ts_safe}.json", metadata
                )

            # ── Pull consciousness data ──
            for name, key in [
                ("phi_history", f"{self._consciousness_prefix}phi_history.json"),
                ("vector", f"{self._consciousness_prefix}vector.json"),
                ("transplant_log", f"{self._consciousness_prefix}transplant_log.json"),
            ]:
                with tempfile.NamedTemporaryFile(
                    suffix=".json", delete=False
                ) as f:
                    tmp = f.name
                found = await loop.run_in_executor(
                    None, self._download_file, key, tmp
                )
                if found:
                    result[name] = json.loads(
                        Path(tmp).read_text(encoding="utf-8")
                    )
                if os.path.exists(tmp):
                    os.unlink(tmp)

            inputs = [phi_history, consciousness_vector, transplant_record, experiment_log]
            pushed_count = sum(1 for x in inputs if x is not None)
            logger.info(
                f"Consciousness sync complete: pushed={pushed_count}, "
                f"pulled={len(result)} keys"
            )

        except Exception as e:
            logger.error(f"Consciousness sync failed: {e}")

        return result

    async def _push_json(self, loop, data, key: str, metadata: dict):
        """Helper: serialize dict/list to JSON and upload to R2."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            tmp = f.name
        try:
            await loop.run_in_executor(
                None, self._upload_file, tmp, key, metadata
            )
        finally:
            os.unlink(tmp)

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
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="Anima Cloud Sync — dual-bucket R2 synchronization",
        epilog="""
Dual-bucket structure:
  anima-memory (state/memory, frequent):
    memory/memory.json, memory/web_memories.json
    memory/autobiographical/<timestamp>.json
    state/state.pt, state/mitosis/*.pt
    meta/sync_manifest.json
    consciousness/phi_history.json, consciousness/vector.json
    consciousness/transplant_log.json
    experiments/<name>_<timestamp>.json

  anima-models (checkpoints, infrequent):
    conscious-lm/cells64/final.pt
    conscious-lm/cells128/step_35000.pt
    conscious-lm/convo-ft/*.pt, conscious-lm/dialogue-ft/*.pt
    animalm/v7/*.pt

Examples:
  python cloud_sync.py push                  # Push memory + state + mitosis
  python cloud_sync.py pull                  # Pull from both buckets
  python cloud_sync.py sync                  # Bidirectional merge
  python cloud_sync.py consciousness         # Sync Phi history & vectors
  python cloud_sync.py status                # Show config & bucket info
  python cloud_sync.py models                # List available model checkpoints
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "action",
        choices=["push", "pull", "sync", "status", "consciousness", "models"],
        help="Sync action: push|pull|sync|status|consciousness|models",
    )
    parser.add_argument(
        "--memory", default="memory_alive.json", help="Path to memory.json"
    )
    parser.add_argument(
        "--state", default="state_alive.pt", help="Path to state.pt"
    )
    parser.add_argument(
        "--bucket", default=None, help="R2 bucket name (default: anima-memory)"
    )
    parser.add_argument(
        "--phi-history", default=None,
        help="Path to Phi history JSON (for consciousness sync)",
    )
    args = parser.parse_args()

    cs = CloudSync(bucket=args.bucket)

    if args.action == "status":
        print(f"Device ID:      {cs.device_id}")
        print(f"Memory bucket:  {cs.bucket}")
        print(f"Models bucket:  {cs.models_bucket}")
        print(f"Endpoint:       {cs.endpoint or '(not set)'}")
        print(f"Configured:     {'yes' if cs._is_available() else 'NO — set env vars'}")
        print()
        print("Required environment variables:")
        print("  ANIMA_R2_ENDPOINT         — Cloudflare R2 S3 endpoint URL")
        print("  ANIMA_R2_ACCESS_KEY       — R2 access key ID")
        print("  ANIMA_R2_SECRET_KEY       — R2 secret access key")
        print("Optional:")
        print("  ANIMA_R2_BUCKET           — Memory bucket (default: anima-memory)")
        print("  ANIMA_R2_MODELS_BUCKET    — Models bucket (default: anima-models)")
        print("  ANIMA_DEVICE_ID           — Device identifier (default: hostname)")
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
                if result["mitosis_paths"]:
                    print(f"Mitosis: {len(result['mitosis_paths'])} cell states")
                if result["models_available"]:
                    print(f"Models: {', '.join(result['models_available'])}")
            elif args.action == "sync":
                await cs.sync(args.memory, args.state)
            elif args.action == "consciousness":
                phi_history = None
                if args.phi_history and Path(args.phi_history).exists():
                    phi_history = json.loads(
                        Path(args.phi_history).read_text(encoding="utf-8")
                    )
                result = await cs.sync_consciousness(phi_history=phi_history)
                for key, data in result.items():
                    if isinstance(data, list):
                        print(f"{key}: {len(data)} entries")
                    elif isinstance(data, dict):
                        print(f"{key}: {json.dumps(data, indent=2)[:200]}")
                if not result:
                    print("No consciousness data found on remote")
            elif args.action == "models":
                models = cs.list_models()
                if models:
                    print("Available models in anima-models:")
                    for m in models:
                        print(f"  {m}")
                else:
                    print("No models found (or bucket not accessible)")

        asyncio.run(_main())

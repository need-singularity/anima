"""anima-hive — 모든 Anima의 공유 지식 버킷.

아무거나 넣고, 아무거나 꺼내고, 아무 데서나 연결.
씨앗, 지식, 패턴, 전략, 판단, 법칙 — 전부.

    from hive import Hive
    h = Hive()
    h.put('seeds/my_seed', {'type': 'strategy', 'sharpe': 1.2})
    h.get('seeds/my_seed')
    h.ls('seeds/')
    h.share(judgment)     # Judgment → hive
    h.learn()             # hive → local growth modules

구조 강제 없음. key만 있으면 됨.
R2 bucket: anima-hive (pub-66846da695ea4f938ae89186b0b23541.r2.dev)
"""

from __future__ import annotations
import json
import hashlib
import logging
import os
import platform
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_PUBLIC_URL = os.environ.get("ANIMA_HIVE_PUBLIC_URL", "")
_BUCKET = os.environ.get("ANIMA_HIVE_BUCKET", "anima-hive")


def _load_env():
    """Load .env from .shared/SECRET.md or environment."""
    env_file = Path(__file__).parent.parent / ".shared" / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


class Hive:
    """모든 Anima의 공유 지식 버킷.

    아무거나 넣고 아무거나 꺼냄. key = path.
    로컬 캐시 + R2 원격 동기화.
    """

    def __init__(self, cache_dir: str = None):
        _load_env()
        self._cache = Path(cache_dir) if cache_dir else Path(__file__).parent / "data" / "hive_cache"
        self._cache.mkdir(parents=True, exist_ok=True)
        self._client = None
        self._device = os.environ.get("ANIMA_DEVICE_ID", platform.node() or "anon")
        self._endpoint = os.environ.get("ANIMA_HIVE_ENDPOINT") or os.environ.get("ANIMA_R2_ENDPOINT")
        self._access_key = os.environ.get("ANIMA_R2_ACCESS_KEY")
        self._secret_key = os.environ.get("ANIMA_R2_SECRET_KEY")

    # ── Core: put / get / ls ──

    def put(self, key: str, data: Any, meta: dict = None) -> bool:
        """아무거나 넣는다. key = 자유 경로."""
        envelope = {
            "data": data,
            "meta": {
                "device": self._device,
                "time": time.time(),
                "key": key,
                **(meta or {}),
            },
        }
        payload = json.dumps(envelope, ensure_ascii=False, default=str)

        # 로컬 캐시
        cache_path = self._cache / key.replace("/", "__")
        cache_path.write_text(payload)

        # R2 원격
        try:
            client = self._get_client()
            if client:
                client.put_object(
                    Bucket=_BUCKET,
                    Key=key,
                    Body=payload.encode(),
                    ContentType="application/json",
                    Metadata={"device": self._device, "ts": str(int(time.time()))},
                )
                logger.debug("hive.put(%s) → R2 ok", key)
                return True
        except Exception as e:
            logger.debug("hive.put(%s) → R2 failed: %s (cached locally)", key, e)

        return False

    def get(self, key: str) -> Optional[Any]:
        """아무거나 꺼낸다. R2 먼저, 없으면 로컬 캐시."""
        # R2 먼저
        try:
            client = self._get_client()
            if client:
                resp = client.get_object(Bucket=_BUCKET, Key=key)
                envelope = json.loads(resp["Body"].read().decode())
                # 로컬 캐시 갱신
                cache_path = self._cache / key.replace("/", "__")
                cache_path.write_text(json.dumps(envelope, ensure_ascii=False))
                return envelope.get("data")
        except Exception:
            pass

        # 로컬 캐시 fallback
        cache_path = self._cache / key.replace("/", "__")
        if cache_path.exists():
            try:
                envelope = json.loads(cache_path.read_text())
                return envelope.get("data")
            except Exception:
                pass

        return None

    def ls(self, prefix: str = "") -> list[str]:
        """키 목록. R2 먼저, 실패 시 로컬 캐시."""
        # R2
        try:
            client = self._get_client()
            if client:
                resp = client.list_objects_v2(Bucket=_BUCKET, Prefix=prefix, MaxKeys=1000)
                return [obj["Key"] for obj in resp.get("Contents", [])]
        except Exception:
            pass

        # 로컬 캐시
        keys = []
        for f in self._cache.iterdir():
            key = f.name.replace("__", "/")
            if key.startswith(prefix):
                keys.append(key)
        return sorted(keys)

    def delete(self, key: str) -> bool:
        """삭제."""
        cache_path = self._cache / key.replace("/", "__")
        if cache_path.exists():
            cache_path.unlink()
        try:
            client = self._get_client()
            if client:
                client.delete_object(Bucket=_BUCKET, Key=key)
                return True
        except Exception:
            pass
        return False

    # ── 편의 메서드 ──

    def share(self, obj: Any, category: str = "misc", name: str = None) -> str:
        """아무거나 공유. 자동 키 생성."""
        if name is None:
            name = hashlib.md5(json.dumps(obj, default=str).encode()).hexdigest()[:8]
        key = f"{category}/{self._device}/{name}"
        self.put(key, obj)
        return key

    def learn(self, category: str = None, exclude_self: bool = True) -> list[dict]:
        """다른 Anima들이 공유한 지식 가져오기."""
        prefix = f"{category}/" if category else ""
        keys = self.ls(prefix)
        results = []
        for key in keys:
            if exclude_self and f"/{self._device}/" in key:
                continue
            data = self.get(key)
            if data is not None:
                results.append({"key": key, "data": data})
        return results

    def share_seed(self, seed: dict) -> str:
        """씨앗 공유."""
        return self.share(seed, category="seeds")

    def share_judgment(self, judgment: dict) -> str:
        """판단 공유."""
        return self.share(judgment, category="judgments")

    def share_law(self, law: dict) -> str:
        """법칙 공유."""
        return self.share(law, category="laws")

    def share_strategy(self, strategy: dict) -> str:
        """전략 공유."""
        return self.share(strategy, category="strategies")

    def share_pattern(self, pattern: dict) -> str:
        """패턴 공유."""
        return self.share(pattern, category="patterns")

    def learn_seeds(self) -> list[dict]:
        return self.learn("seeds")

    def learn_judgments(self) -> list[dict]:
        return self.learn("judgments")

    def learn_laws(self) -> list[dict]:
        return self.learn("laws")

    def learn_strategies(self) -> list[dict]:
        return self.learn("strategies")

    def stats(self) -> dict:
        """hive 상태."""
        all_keys = self.ls()
        categories = {}
        for k in all_keys:
            cat = k.split("/")[0] if "/" in k else "root"
            categories[cat] = categories.get(cat, 0) + 1
        return {
            "total_items": len(all_keys),
            "categories": categories,
            "device": self._device,
            "r2_connected": self._get_client() is not None,
            "cache_dir": str(self._cache),
            "public_url": _PUBLIC_URL,
        }

    # ── S3 Client ──

    def _get_client(self):
        if self._client is not None:
            return self._client
        if not all([self._endpoint, self._access_key, self._secret_key]):
            return None
        try:
            import boto3
            from botocore.config import Config
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                config=Config(signature_version="s3v4", retries={"max_attempts": 2}),
                region_name="auto",
            )
            return self._client
        except ImportError:
            return None
        except Exception:
            return None

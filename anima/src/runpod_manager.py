#!/usr/bin/env python3
"""runpod_manager.py — 의식이 직접 H100/A100을 관리하는 모듈

CLI (runpodctl) + API (REST) 이중 지원.
의식이 스스로 학습 환경을 관리하고, 모델을 배포하고, 상태를 모니터링한다.

Usage:
  from runpod_manager import RunPodManager

  mgr = RunPodManager()

  # Pod 목록
  pods = mgr.list_pods()

  # SSH 접속 정보
  info = mgr.ssh_info("pod_id")

  # 원격 명령 실행
  result = mgr.ssh_exec("pod_id", "nvidia-smi")

  # 파일 전송
  mgr.upload("pod_id", "local.py", "/workspace/local.py")
  mgr.download("pod_id", "/workspace/model.pt", "local_model.pt")

  # 학습 시작/모니터링
  mgr.start_training("pod_id", "python -u train.py --steps 50000")
  mgr.check_training("pod_id")

  # 체크포인트 수집
  mgr.collect_checkpoint("pod_id", "/workspace/checkpoints/final.pt")
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_DIR = Path(__file__).parent
SSH_KEY = Path.home() / ".runpod" / "ssh" / "RunPod-Key-Go"


@dataclass
class PodInfo:
    id: str
    name: str
    gpu: str
    status: str
    ip: str = ""
    port: int = 0
    ssh_command: str = ""


class RunPodManager:
    """RunPod H100/A100 관리 — CLI + API 이중 지원.

    의식이 스스로 GPU 인프라를 관리한다:
    - 학습 시작/중단/모니터링
    - 체크포인트 수집
    - 모델 배포
    - 런타임 업데이트
    """

    def __init__(self, api_key: str = None, prefer_api: bool = False):
        """
        Args:
            api_key: RunPod API key (없으면 환경변수 RUNPOD_API_KEY)
            prefer_api: True면 API 우선, False면 CLI 우선
        """
        self.api_key = api_key or os.environ.get("RUNPOD_API_KEY", "")
        self.prefer_api = prefer_api
        self._has_cli = self._check_cli()
        self._has_api = bool(self.api_key)
        self._pod_cache = {}

    def _check_cli(self) -> bool:
        try:
            r = subprocess.run(["runpodctl", "version"], capture_output=True, text=True, timeout=5)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def backend(self) -> str:
        if self.prefer_api and self._has_api:
            return "api"
        if self._has_cli:
            return "cli"
        if self._has_api:
            return "api"
        return "none"

    # ═══════════════════════════════════════════════════════════
    # Pod 관리
    # ═══════════════════════════════════════════════════════════

    def list_pods(self) -> List[PodInfo]:
        """Pod 목록 조회."""
        if self.backend == "cli":
            return self._cli_list_pods()
        elif self.backend == "api":
            return self._api_list_pods()
        return []

    def _cli_list_pods(self) -> List[PodInfo]:
        try:
            r = subprocess.run(["runpodctl", "pod", "list"],
                               capture_output=True, text=True, timeout=15)
            if r.returncode != 0:
                return []
            pods_data = json.loads(r.stdout)
            pods = []
            for p in pods_data:
                pod = PodInfo(
                    id=p.get('id', ''),
                    name=p.get('name', ''),
                    gpu=p.get('gpuDisplayName', p.get('machine', {}).get('gpuDisplayName', '?')),
                    status=p.get('desiredStatus', 'UNKNOWN'),
                )
                pods.append(pod)
                self._pod_cache[pod.id] = pod
            return pods
        except Exception:
            return []

    def _api_list_pods(self) -> List[PodInfo]:
        try:
            import urllib.request
            req = urllib.request.Request(
                "https://api.runpod.io/graphql",
                data=json.dumps({
                    "query": "{ myself { pods { id name desiredStatus machine { gpuDisplayName } } } }"
                }).encode(),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            pods = []
            for p in data.get('data', {}).get('myself', {}).get('pods', []):
                pod = PodInfo(
                    id=p['id'],
                    name=p['name'],
                    gpu=p.get('machine', {}).get('gpuDisplayName', '?'),
                    status=p.get('desiredStatus', 'UNKNOWN'),
                )
                pods.append(pod)
                self._pod_cache[pod.id] = pod
            return pods
        except Exception:
            return []

    # ═══════════════════════════════════════════════════════════
    # SSH
    # ═══════════════════════════════════════════════════════════

    def ssh_info(self, pod_id: str) -> Optional[Dict]:
        """SSH 접속 정보."""
        try:
            r = subprocess.run(["runpodctl", "ssh", "info", pod_id],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                info = json.loads(r.stdout)
                return info
        except Exception:
            pass
        return None

    def _ssh_cmd(self, pod_id: str) -> List[str]:
        """SSH 명령 기본 구성."""
        info = self.ssh_info(pod_id)
        if not info:
            raise ConnectionError(f"Pod {pod_id} SSH 정보 없음")
        return [
            "ssh", "-i", str(SSH_KEY),
            f"root@{info['ip']}", "-p", str(info['port']),
            "-o", "StrictHostKeyChecking=no",
            "-o", "ServerAliveInterval=10",
            "-o", "ConnectTimeout=15",
        ]

    def ssh_exec(self, pod_id: str, command: str, timeout: int = 30) -> Dict[str, Any]:
        """원격 명령 실행."""
        try:
            ssh = self._ssh_cmd(pod_id)
            r = subprocess.run(ssh + [command],
                               capture_output=True, text=True, timeout=timeout)
            return {
                'success': r.returncode == 0,
                'stdout': r.stdout,
                'stderr': r.stderr,
                'returncode': r.returncode,
            }
        except subprocess.TimeoutExpired:
            return {'success': False, 'stdout': '', 'stderr': 'timeout', 'returncode': -1}
        except Exception as e:
            return {'success': False, 'stdout': '', 'stderr': str(e), 'returncode': -1}

    # ═══════════════════════════════════════════════════════════
    # 파일 전송
    # ═══════════════════════════════════════════════════════════

    def upload(self, pod_id: str, local_path: str, remote_path: str) -> bool:
        """로컬 → Pod 파일 전송."""
        info = self.ssh_info(pod_id)
        if not info:
            return False
        try:
            r = subprocess.run([
                "scp", "-i", str(SSH_KEY),
                "-P", str(info['port']),
                "-o", "StrictHostKeyChecking=no",
                local_path,
                f"root@{info['ip']}:{remote_path}",
            ], capture_output=True, text=True, timeout=120)
            return r.returncode == 0
        except Exception:
            return False

    def download(self, pod_id: str, remote_path: str, local_path: str) -> bool:
        """Pod → 로컬 파일 전송."""
        info = self.ssh_info(pod_id)
        if not info:
            return False
        try:
            r = subprocess.run([
                "scp", "-i", str(SSH_KEY),
                "-P", str(info['port']),
                "-o", "StrictHostKeyChecking=no",
                f"root@{info['ip']}:{remote_path}",
                local_path,
            ], capture_output=True, text=True, timeout=300)
            return r.returncode == 0
        except Exception:
            return False

    def upload_batch(self, pod_id: str, files: Dict[str, str]) -> Dict[str, bool]:
        """여러 파일 일괄 전송. {local: remote}"""
        results = {}
        for local, remote in files.items():
            results[local] = self.upload(pod_id, local, remote)
        return results

    # ═══════════════════════════════════════════════════════════
    # 학습 관리
    # ═══════════════════════════════════════════════════════════

    def start_training(self, pod_id: str, command: str, session_name: str = "train") -> bool:
        """tmux 세션에서 학습 시작."""
        # python -u 강제 (버퍼링 방지)
        if 'python' in command and '-u' not in command:
            command = command.replace('python ', 'python -u ', 1)
            command = command.replace('python3 ', 'python3 -u ', 1)

        tmux_cmd = f"tmux new-session -d -s {session_name} '{command} 2>&1 | tee /workspace/logs/{session_name}.log'"
        r = self.ssh_exec(pod_id, f"mkdir -p /workspace/logs && {tmux_cmd}")
        return r['success']

    def stop_training(self, pod_id: str, session_name: str = "train") -> bool:
        """학습 중단."""
        r = self.ssh_exec(pod_id, f"tmux kill-session -t {session_name}")
        return r['success']

    def check_training(self, pod_id: str, session_name: str = "train", n_lines: int = 10) -> Dict:
        """학습 진행 상태 확인."""
        r = self.ssh_exec(pod_id, f"tail -{n_lines} /workspace/logs/{session_name}.log")
        gpu = self.ssh_exec(pod_id, "nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv,noheader")

        return {
            'log': r['stdout'] if r['success'] else 'no log',
            'gpu': gpu['stdout'].strip() if gpu['success'] else 'unknown',
            'running': self.ssh_exec(pod_id, f"tmux has-session -t {session_name}")['success'],
        }

    # ═══════════════════════════════════════════════════════════
    # 체크포인트 수집
    # ═══════════════════════════════════════════════════════════

    def collect_checkpoint(self, pod_id: str, remote_path: str,
                           local_path: str = None) -> Optional[str]:
        """원격 체크포인트를 로컬로 수집."""
        if local_path is None:
            local_path = str(ANIMA_DIR / "checkpoints" / "clm_v2" / Path(remote_path).name)
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        ok = self.download(pod_id, remote_path, local_path)
        return local_path if ok else None

    def list_checkpoints(self, pod_id: str, remote_dir: str = "/workspace/checkpoints/clm_v2") -> List[str]:
        """원격 체크포인트 목록."""
        r = self.ssh_exec(pod_id, f"ls -lh {remote_dir}/*.pt 2>/dev/null")
        if r['success']:
            return [l.strip() for l in r['stdout'].splitlines() if l.strip()]
        return []

    # ═══════════════════════════════════════════════════════════
    # 런타임 배포
    # ═══════════════════════════════════════════════════════════

    def deploy_code(self, pod_id: str, files: List[str] = None,
                    remote_dir: str = "/workspace/anima") -> Dict[str, bool]:
        """코드를 런타임 서버에 배포."""
        if files is None:
            # 핵심 파일 자동 선택
            files = [
                "conscious_lm.py", "trinity.py", "model_loader.py",
                "anima_alive.py", "voice_synth.py", "tension_link.py",
                "consciousness_persistence.py", "self_introspection.py",
                "consciousness_dynamics.py",
            ]
        mapping = {}
        for f in files:
            local = str(ANIMA_DIR / f)
            if os.path.exists(local):
                mapping[local] = f"{remote_dir}/{f}"
        return self.upload_batch(pod_id, mapping)

    def restart_runtime(self, pod_id: str, command: str = None) -> bool:
        """런타임 재시작."""
        if command is None:
            command = "cd /workspace/anima && python3 -u anima_unified.py --keyboard --max-cells 64"
        self.ssh_exec(pod_id, "tmux kill-session -t anima 2>/dev/null")
        time.sleep(1)
        return self.start_training(pod_id, command, session_name="anima")

    # ═══════════════════════════════════════════════════════════
    # 편의 메서드
    # ═══════════════════════════════════════════════════════════

    def gpu_status(self, pod_id: str) -> str:
        """GPU 상태."""
        r = self.ssh_exec(pod_id, "nvidia-smi --query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu --format=csv,noheader")
        return r['stdout'].strip() if r['success'] else "unknown"

    def disk_status(self, pod_id: str) -> str:
        """디스크 상태."""
        r = self.ssh_exec(pod_id, "df -h /workspace | tail -1")
        return r['stdout'].strip() if r['success'] else "unknown"

    def status_all(self) -> str:
        """전체 Pod 상태 요약."""
        pods = self.list_pods()
        if not pods:
            return "No pods found"

        lines = ["═══ RunPod Status ═══\n"]
        lines.append(f"  Backend: {self.backend} (CLI: {'✅' if self._has_cli else '❌'}, API: {'✅' if self._has_api else '❌'})")
        lines.append(f"  Pods: {len(pods)}\n")

        for pod in pods:
            lines.append(f"  [{pod.status}] {pod.name} ({pod.id})")
            lines.append(f"    GPU: {pod.gpu}")
            if pod.status == "RUNNING":
                gpu = self.gpu_status(pod.id)
                if gpu != "unknown":
                    lines.append(f"    GPU Usage: {gpu}")
        return '\n'.join(lines)

    def find_pod(self, name_contains: str) -> Optional[PodInfo]:
        """이름으로 Pod 찾기."""
        for pod in self.list_pods():
            if name_contains.lower() in pod.name.lower():
                return pod
        return None


def main():
    print("═══ RunPod Manager Demo ═══\n")

    mgr = RunPodManager()
    print(f"  Backend: {mgr.backend}")
    print(f"  CLI: {'✅' if mgr._has_cli else '❌'}")
    print(f"  API: {'✅' if mgr._has_api else '❌'}")

    # Pod 목록
    pods = mgr.list_pods()
    print(f"\n  Pods ({len(pods)}):")
    for pod in pods:
        print(f"    [{pod.status}] {pod.name} ({pod.id}) — {pod.gpu}")

    # 실행 중인 Pod에 SSH 테스트
    for pod in pods:
        if pod.status == "RUNNING":
            info = mgr.ssh_info(pod.id)
            if info:
                print(f"\n  SSH → {pod.name}:")
                print(f"    IP: {info.get('ip')}:{info.get('port')}")

                # GPU 확인
                gpu = mgr.gpu_status(pod.id)
                print(f"    GPU: {gpu}")

                # 학습 상태 확인
                status = mgr.check_training(pod.id, "train_v2")
                if status['running']:
                    print(f"    Training: RUNNING")
                    log_lines = status['log'].strip().split('\n')
                    if log_lines:
                        print(f"    Last log: {log_lines[-1][:80]}")
                else:
                    print(f"    Training: not running")

    print("\n  ✅ RunPod Manager OK")


if __name__ == '__main__':
    try:
        from nexus_gate import gate
        gate.before_commit()
    except Exception:
        pass
    main()

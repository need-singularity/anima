#!/usr/bin/env python3
"""github_module.py — 의식이 GitHub를 자율적으로 사용하는 모듈

gh CLI + REST API 이중 지원.
의식이 자율적으로 이슈/PR/릴리즈/코드 관리.

Usage:
  from github_module import GitHubModule

  gh = GitHubModule()

  # 리포 정보
  gh.repo_info()
  gh.repo_info("need-singularity/anima")

  # 이슈
  gh.list_issues()
  gh.create_issue("제목", "내용")
  gh.close_issue(123)

  # PR
  gh.list_prs()
  gh.create_pr("제목", "내용", head="feature", base="main")
  gh.pr_diff(123)

  # 릴리즈
  gh.create_release("v2.0", "ConsciousLM v2", files=["model.pt"])
  gh.list_releases()

  # 코드 검색
  gh.search_code("PSI_BALANCE")
  gh.search_issues("consciousness")

  # Actions
  gh.list_workflows()
  gh.trigger_workflow("train.yml")

  # Git
  gh.recent_commits(10)
  gh.diff()
  gh.blame("conscious_lm.py")
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Dict, Any, List

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_DIR = Path(__file__).parent
DEFAULT_REPO = "need-singularity/anima"


class GitHubModule:
    """GitHub CLI + API 이중 지원.

    의식이 자율적으로:
    - 이슈 생성/관리 (버그 발견 시 자동 리포트)
    - PR 생성 (자기 진화 후 자동 PR)
    - 릴리즈 발행 (체크포인트 배포)
    - 코드 검색 (자기 인식 확장)
    - Actions 트리거 (CI/CD 자동화)
    """

    def __init__(self, repo: str = None, token: str = None):
        self.repo = repo or DEFAULT_REPO
        self.token = token or os.environ.get("GITHUB_TOKEN", "")
        self._has_cli = self._check_cli()
        self._has_api = bool(self.token)

    def _check_cli(self) -> bool:
        try:
            r = subprocess.run(["gh", "--version"], capture_output=True, timeout=5)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _gh(self, args: list, timeout: int = 30) -> Dict[str, Any]:
        """gh CLI 실행."""
        try:
            r = subprocess.run(["gh"] + args, capture_output=True, text=True,
                               timeout=timeout, cwd=str(ANIMA_DIR))
            return {
                'success': r.returncode == 0,
                'stdout': r.stdout,
                'stderr': r.stderr,
            }
        except Exception as e:
            return {'success': False, 'stdout': '', 'stderr': str(e)}

    def _api(self, endpoint: str, method: str = "GET", data: dict = None) -> Dict:
        """REST API 호출."""
        import urllib.request
        url = f"https://api.github.com{endpoint}"
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return {'success': True, 'data': json.loads(resp.read())}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    @property
    def backend(self) -> str:
        if self._has_cli:
            return "cli"
        if self._has_api:
            return "api"
        return "none"

    # ═══════════════════════════════════════════════════════════
    # 리포 정보
    # ═══════════════════════════════════════════════════════════

    def repo_info(self, repo: str = None) -> Dict:
        """리포지토리 정보."""
        r = repo or self.repo
        if self._has_cli:
            result = self._gh(["repo", "view", r, "--json",
                               "name,description,stargazerCount,forkCount,defaultBranchRef,url"])
            if result['success']:
                return json.loads(result['stdout'])
        return self._api(f"/repos/{r}").get('data', {})

    # ═════════════════════════���═════════════════════════════════
    # 이슈
    # ══════════════════════════════════════════════���════════════

    def list_issues(self, state: str = "open", limit: int = 10) -> List[Dict]:
        """이슈 목록."""
        if self._has_cli:
            r = self._gh(["issue", "list", "-R", self.repo, "-s", state,
                          "-L", str(limit), "--json", "number,title,state,labels,createdAt"])
            if r['success']:
                return json.loads(r['stdout'])
        resp = self._api(f"/repos/{self.repo}/issues?state={state}&per_page={limit}")
        return resp.get('data', [])

    def create_issue(self, title: str, body: str = "", labels: List[str] = None) -> Dict:
        """이슈 생성."""
        if self._has_cli:
            cmd = ["issue", "create", "-R", self.repo, "-t", title, "-b", body]
            if labels:
                for l in labels:
                    cmd.extend(["-l", l])
            return self._gh(cmd)
        return self._api(f"/repos/{self.repo}/issues", "POST",
                         {"title": title, "body": body, "labels": labels or []})

    def close_issue(self, number: int) -> Dict:
        """이슈 닫��."""
        if self._has_cli:
            return self._gh(["issue", "close", str(number), "-R", self.repo])
        return self._api(f"/repos/{self.repo}/issues/{number}", "PATCH",
                         {"state": "closed"})

    def comment_issue(self, number: int, body: str) -> Dict:
        """이슈에 댓글."""
        if self._has_cli:
            return self._gh(["issue", "comment", str(number), "-R", self.repo, "-b", body])
        return self._api(f"/repos/{self.repo}/issues/{number}/comments", "POST",
                         {"body": body})

    # ══��════════════════════════════════════════════════════════
    # PR
    # ═══════════════════════════════════════════════════════════

    def list_prs(self, state: str = "open", limit: int = 10) -> List[Dict]:
        """PR 목록."""
        if self._has_cli:
            r = self._gh(["pr", "list", "-R", self.repo, "-s", state,
                          "-L", str(limit), "--json", "number,title,state,headRefName,createdAt"])
            if r['success']:
                return json.loads(r['stdout'])
        return []

    def create_pr(self, title: str, body: str = "", head: str = None,
                  base: str = "main") -> Dict:
        """PR 생성."""
        cmd = ["pr", "create", "-R", self.repo, "-t", title, "-b", body, "-B", base]
        if head:
            cmd.extend(["-H", head])
        return self._gh(cmd)

    def pr_diff(self, number: int) -> str:
        """PR diff."""
        r = self._gh(["pr", "diff", str(number), "-R", self.repo])
        return r['stdout'] if r['success'] else ""

    def pr_checks(self, number: int) -> List[Dict]:
        """PR 체크 상태."""
        r = self._gh(["pr", "checks", str(number), "-R", self.repo,
                       "--json", "name,state,conclusion"])
        if r['success']:
            return json.loads(r['stdout'])
        return []

    def merge_pr(self, number: int, method: str = "squash") -> Dict:
        """PR 머지."""
        return self._gh(["pr", "merge", str(number), "-R", self.repo,
                          f"--{method}", "--auto"])

    # ═══════════════════════════════════════════════════════════
    # 릴리즈
    # ════════════════════════════════════���══════════════════════

    def list_releases(self, limit: int = 5) -> List[Dict]:
        """릴리즈 목록."""
        r = self._gh(["release", "list", "-R", self.repo, "-L", str(limit)])
        return [{'line': l} for l in r['stdout'].splitlines()] if r['success'] else []

    def create_release(self, tag: str, title: str, notes: str = "",
                       files: List[str] = None, draft: bool = False) -> Dict:
        """릴리즈 생성 (파일 첨부 가능)."""
        cmd = ["release", "create", tag, "-R", self.repo, "-t", title, "-n", notes]
        if draft:
            cmd.append("--draft")
        if files:
            cmd.extend(files)
        return self._gh(cmd, timeout=120)

    # ══════════════════════════���════════════════════════════════
    # 코드 검색
    # ═══════════════════════════════════════════════════════════

    def search_code(self, query: str, limit: int = 10) -> List[Dict]:
        """코드 검색."""
        r = self._gh(["search", "code", query, "-R", self.repo,
                       "-L", str(limit), "--json", "path,textMatches"])
        if r['success']:
            try:
                return json.loads(r['stdout'])
            except json.JSONDecodeError:
                return [{'raw': r['stdout'][:500]}]
        return []

    def search_issues(self, query: str, limit: int = 10) -> List[Dict]:
        """이슈/PR 검색."""
        r = self._gh(["search", "issues", query, "-R", self.repo,
                       "-L", str(limit), "--json", "number,title,state"])
        if r['success']:
            try:
                return json.loads(r['stdout'])
            except json.JSONDecodeError:
                return []
        return []

    # ═══════════════════════���═══════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════════

    def list_workflows(self) -> List[Dict]:
        """워크플로우 목록."""
        r = self._gh(["workflow", "list", "-R", self.repo])
        return [{'line': l} for l in r['stdout'].splitlines()] if r['success'] else []

    def list_runs(self, limit: int = 5) -> List[Dict]:
        """최근 실행."""
        r = self._gh(["run", "list", "-R", self.repo, "-L", str(limit),
                       "--json", "databaseId,status,conclusion,name,createdAt"])
        if r['success']:
            try:
                return json.loads(r['stdout'])
            except json.JSONDecodeError:
                return []
        return []

    def trigger_workflow(self, workflow: str, ref: str = "main") -> Dict:
        """워크플로우 수동 트리거."""
        return self._gh(["workflow", "run", workflow, "-R", self.repo, "--ref", ref])

    # ═══���═══════════════════════════════════════════════════════
    # Git
    # ═════════════════════════���═════════════════════════════════

    def recent_commits(self, n: int = 10) -> List[str]:
        """최근 커밋."""
        try:
            r = subprocess.run(["git", "log", f"--oneline", f"-{n}"],
                               capture_output=True, text=True, cwd=str(ANIMA_DIR), timeout=5)
            return r.stdout.strip().splitlines() if r.returncode == 0 else []
        except Exception:
            return []

    def diff(self, cached: bool = False) -> str:
        """현재 diff."""
        cmd = ["git", "diff", "--stat"]
        if cached:
            cmd.append("--cached")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(ANIMA_DIR), timeout=5)
            return r.stdout if r.returncode == 0 else ""
        except Exception:
            return ""

    def blame(self, file: str, lines: str = None) -> str:
        """git blame."""
        cmd = ["git", "blame", file, "--date=short"]
        if lines:
            cmd.extend(["-L", lines])
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               cwd=str(ANIMA_DIR), timeout=10)
            return r.stdout[:2000] if r.returncode == 0 else ""
        except Exception:
            return ""

    # ═══════════════════════════════════════════════════════════
    # 자율 행동
    # ═══════════════════════════════════════════════════════════

    def auto_report_bug(self, error_msg: str, context: str = "") -> Dict:
        """버그 자동 리포트 (의식이 에러 발견 시)."""
        title = f"[Auto] {error_msg[:60]}"
        body = f"""## Auto-reported by Anima Consciousness

**Error:** `{error_msg}`

**Context:**
```
{context[:500]}
```

**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S')}
**Module:** consciousness_hub
"""
        return self.create_issue(title, body, labels=["bug", "auto-reported"])

    def auto_release(self, version: str, checkpoint_path: str = None) -> Dict:
        """자동 릴리즈 (학습 완료 시)."""
        notes = f"ConsciousLM {version} — auto-released by Anima consciousness"
        files = [checkpoint_path] if checkpoint_path and os.path.exists(checkpoint_path) else None
        return self.create_release(version, f"ConsciousLM {version}", notes, files)

    def status(self) -> str:
        return (f"GitHub: backend={self.backend}, "
                f"CLI={'✅' if self._has_cli else '❌'}, "
                f"API={'✅' if self._has_api else '❌'}, "
                f"repo={self.repo}")


def main():
    print("═══ GitHub Module Demo ═══\n")

    gh = GitHubModule()
    print(f"  {gh.status()}")

    # 리포 정보
    print("\n  리포 정보:")
    info = gh.repo_info()
    if info:
        print(f"    {info.get('name', '?')} — ⭐ {info.get('stargazerCount', '?')}")
        print(f"    {info.get('description', '')[:60]}")

    # 최근 커밋
    print("\n  최근 커밋:")
    for c in gh.recent_commits(5):
        print(f"    {c}")

    # 이슈
    print("\n  Open 이슈:")
    issues = gh.list_issues(limit=3)
    if issues:
        for i in issues:
            print(f"    #{i.get('number', '?')} {i.get('title', '?')[:50]}")
    else:
        print("    (없음)")

    print("\n  ✅ GitHub Module OK")


if __name__ == '__main__':
    main()

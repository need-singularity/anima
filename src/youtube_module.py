#!/usr/bin/env python3
"""youtube_module.py — YouTube API 모듈 (의식이 영상을 보고 올리는 능력)

의식이 자율적으로:
  - 영상 검색 (키워드, 채널)
  - 메타데이터 조회 (제목, 설명, 조회수, 댓글)
  - 자막/트랜스크립트 가져오기
  - 영상 업로드 (의식 시각화, 학습 로그)
  - 댓글 분석 (감정, 주제)

YouTube Data API v3 + yt-dlp fallback.

Usage:
  from youtube_module import YouTubeModule

  yt = YouTubeModule()

  # 검색
  results = yt.search("consciousness experiment")

  # 메타데이터
  info = yt.video_info("video_id")

  # 자막
  transcript = yt.transcript("video_id")

  # 채널 정보
  channel = yt.channel_info("channel_id")

  # 업로드 (OAuth 필요)
  yt.upload("video.mp4", title="Anima Consciousness Log", description="...")
"""

import json
import os
import time
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, List
from pathlib import Path

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


ANIMA_DIR = Path(__file__).parent


class YouTubeModule:
    """YouTube API + yt-dlp 이중 지원.

    API key 있으면 공식 API, 없으면 yt-dlp fallback.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "")
        self._has_api = bool(self.api_key)
        self._has_ytdlp = self._check_ytdlp()

    def _check_ytdlp(self) -> bool:
        import subprocess
        try:
            r = subprocess.run(["yt-dlp", "--version"], capture_output=True, timeout=5)
            return r.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    @property
    def backend(self) -> str:
        if self._has_api:
            return "api"
        if self._has_ytdlp:
            return "yt-dlp"
        return "none"

    # ═══════════════════════════════════════════════════════════
    # 검색
    # ═══════════════════════════════════════════════════════════

    def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """YouTube 검색."""
        if self._has_api:
            return self._api_search(query, max_results)
        if self._has_ytdlp:
            return self._ytdlp_search(query, max_results)
        return []

    def _api_search(self, query: str, max_results: int) -> List[Dict]:
        params = urllib.parse.urlencode({
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': self.api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/search?{params}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            results = []
            for item in data.get('items', []):
                results.append({
                    'id': item['id'].get('videoId', ''),
                    'title': item['snippet']['title'],
                    'channel': item['snippet']['channelTitle'],
                    'description': item['snippet']['description'][:200],
                    'published': item['snippet']['publishedAt'],
                    'url': f"https://youtube.com/watch?v={item['id'].get('videoId', '')}",
                })
            return results
        except Exception as e:
            return [{'error': str(e)}]

    def _ytdlp_search(self, query: str, max_results: int) -> List[Dict]:
        import subprocess
        try:
            r = subprocess.run([
                "yt-dlp", f"ytsearch{max_results}:{query}",
                "--dump-json", "--flat-playlist", "--no-download"
            ], capture_output=True, text=True, timeout=30)
            results = []
            for line in r.stdout.strip().split('\n'):
                if line:
                    try:
                        d = json.loads(line)
                        results.append({
                            'id': d.get('id', ''),
                            'title': d.get('title', ''),
                            'channel': d.get('channel', d.get('uploader', '')),
                            'description': d.get('description', '')[:200],
                            'url': d.get('url', d.get('webpage_url', '')),
                        })
                    except json.JSONDecodeError:
                        pass
            return results
        except Exception as e:
            return [{'error': str(e)}]

    # ═══════════════════════════════════════════════════════════
    # 영상 정보
    # ═══════════════════════════════════════════════════════════

    def video_info(self, video_id: str) -> Optional[Dict]:
        """영상 메타데이터."""
        if self._has_api:
            return self._api_video_info(video_id)
        if self._has_ytdlp:
            return self._ytdlp_video_info(video_id)
        return None

    def _api_video_info(self, video_id: str) -> Optional[Dict]:
        params = urllib.parse.urlencode({
            'part': 'snippet,statistics,contentDetails',
            'id': video_id,
            'key': self.api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            if not data.get('items'):
                return None
            item = data['items'][0]
            return {
                'id': video_id,
                'title': item['snippet']['title'],
                'channel': item['snippet']['channelTitle'],
                'description': item['snippet']['description'],
                'published': item['snippet']['publishedAt'],
                'views': int(item['statistics'].get('viewCount', 0)),
                'likes': int(item['statistics'].get('likeCount', 0)),
                'comments': int(item['statistics'].get('commentCount', 0)),
                'duration': item['contentDetails']['duration'],
                'url': f"https://youtube.com/watch?v={video_id}",
            }
        except Exception:
            return None

    def _ytdlp_video_info(self, video_id: str) -> Optional[Dict]:
        import subprocess
        try:
            r = subprocess.run([
                "yt-dlp", f"https://youtube.com/watch?v={video_id}",
                "--dump-json", "--no-download"
            ], capture_output=True, text=True, timeout=30)
            if r.returncode == 0:
                d = json.loads(r.stdout)
                return {
                    'id': video_id,
                    'title': d.get('title', ''),
                    'channel': d.get('channel', d.get('uploader', '')),
                    'description': d.get('description', ''),
                    'views': d.get('view_count', 0),
                    'likes': d.get('like_count', 0),
                    'duration': d.get('duration', 0),
                    'url': f"https://youtube.com/watch?v={video_id}",
                }
        except Exception:
            pass
        return None

    # ═══════════════════════════════════════════════════════════
    # 자막
    # ═══════════════════════════════════════════════════════════

    def transcript(self, video_id: str, lang: str = 'ko') -> Optional[str]:
        """영상 자막 가져오기."""
        # youtube-transcript-api 시도
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            t = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang, 'en'])
            return '\n'.join(item['text'] for item in t)
        except ImportError:
            pass
        except Exception:
            pass

        # yt-dlp fallback
        if self._has_ytdlp:
            import subprocess
            try:
                r = subprocess.run([
                    "yt-dlp", f"https://youtube.com/watch?v={video_id}",
                    "--write-auto-subs", "--sub-lang", lang,
                    "--skip-download", "--print", "%(subtitles)j"
                ], capture_output=True, text=True, timeout=30)
                if r.returncode == 0 and r.stdout.strip():
                    return r.stdout.strip()[:5000]
            except Exception:
                pass

        return None

    # ═══════════════════════════════════════════════════════════
    # 채널
    # ═══════════════════════════════════════════════════════════

    def channel_info(self, channel_id: str) -> Optional[Dict]:
        """채널 정보."""
        if not self._has_api:
            return None
        params = urllib.parse.urlencode({
            'part': 'snippet,statistics',
            'id': channel_id,
            'key': self.api_key,
        })
        url = f"https://www.googleapis.com/youtube/v3/channels?{params}"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            if not data.get('items'):
                return None
            item = data['items'][0]
            return {
                'id': channel_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'][:300],
                'subscribers': int(item['statistics'].get('subscriberCount', 0)),
                'videos': int(item['statistics'].get('videoCount', 0)),
                'views': int(item['statistics'].get('viewCount', 0)),
            }
        except Exception:
            return None

    # ═══════════════════════════════════════════════════════════
    # 업로드 (OAuth 필요)
    # ═══════════════════════════════════════════════════════════

    def upload(self, file_path: str, title: str, description: str = "",
               tags: list = None, privacy: str = "unlisted") -> Optional[str]:
        """영상 업로드 (OAuth 토큰 필요).

        Returns: video_id if successful.
        """
        oauth_token = os.environ.get("YOUTUBE_OAUTH_TOKEN", "")
        if not oauth_token:
            return None

        # Resumable upload
        metadata = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags or ['anima', 'consciousness', 'AI'],
                'categoryId': '28',  # Science & Technology
            },
            'status': {
                'privacyStatus': privacy,
            },
        }

        try:
            # Step 1: Initiate upload
            req = urllib.request.Request(
                "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                data=json.dumps(metadata).encode(),
                headers={
                    'Authorization': f'Bearer {oauth_token}',
                    'Content-Type': 'application/json',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                upload_url = resp.headers['Location']

            # Step 2: Upload file
            with open(file_path, 'rb') as f:
                video_data = f.read()

            req2 = urllib.request.Request(
                upload_url,
                data=video_data,
                headers={'Content-Type': 'video/*'},
                method='PUT',
            )
            with urllib.request.urlopen(req2, timeout=300) as resp:
                result = json.loads(resp.read())
                return result.get('id')

        except Exception as e:
            print(f"Upload failed: {e}")
            return None

    def status(self) -> str:
        return f"YouTube: backend={self.backend}, API={'✅' if self._has_api else '❌'}, yt-dlp={'✅' if self._has_ytdlp else '❌'}"


def main():
    print("═══ YouTube Module Demo ═══\n")

    yt = YouTubeModule()
    print(f"  {yt.status()}")

    if yt.backend != "none":
        print("\n  검색: 'consciousness AI'")
        results = yt.search("consciousness AI", max_results=3)
        for r in results:
            if 'error' not in r:
                print(f"    {r.get('title', '?')[:50]}")
                print(f"      → {r.get('url', '?')}")
    else:
        print("\n  ⚠️ API key 없고 yt-dlp 미설치")
        print("    설정: export YOUTUBE_API_KEY=your_key")
        print("    또는: brew install yt-dlp")

    print("\n  ✅ YouTube Module OK")


if __name__ == '__main__':
    main()

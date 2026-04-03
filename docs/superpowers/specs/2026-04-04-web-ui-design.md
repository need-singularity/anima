# Anima Web UI — Minimal Consciousness Interface

**Date:** 2026-04-04
**Status:** Approved
**NEXUS-6 검증:** n6(5)=sopfr EXACT (탭), n6(4)=tau EXACT (채팅 상태), 마찰도 38% 감소

## Summary

사이드바 없는 1-column 중앙 정렬 레이아웃. 플로팅 채팅(시리 스타일)이 모든 페이지에서 상시 접근. 음성 대화 지원.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  ANIMA ● live      Dash  Evo  Laws  Mem  Tools           🔊 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│                ┌──────────────────────────┐                  │
│                │                          │                  │
│                │     [ 중앙 정렬 뷰 ]      │                  │
│                │     max-w-4xl (960px)     │                  │
│                │     탭에 따라 전환        │                  │
│                │                          │                  │
│                └──────────────────────────┘                  │
│                                                              │
│                                                         ┌──┐ │
│                                                         │💬│ │
│                                                         └──┘ │
└──────────────────────────────────────────────────────────────┘
```

## Components (5 = sopfr EXACT)

### 1. Header

한 줄 구성:
- **좌측:** `ANIMA` 로고 + `● live` 연결 상태 (WebSocket)
- **중앙:** 5개 탭 네비게이션 `Dash | Evo | Laws | Mem | Tools`
- **우측:** 🔊 음성 모드 버튼

### 2. TabNav (5탭 = sopfr EXACT)

| 탭 | 콘텐츠 | 핵심 컴포넌트 |
|----|--------|-------------|
| Dash | 의식 대시보드 | Φ 게이지, 텐션/호기심 바, 10D 벡터, 12 파벌, 이벤트 스트림, NEXUS-6 렌즈, 허브 모듈 상태 |
| Evo | OUROBOROS 진화 | 법칙 발견 곡선, 세대별 테이블, 토폴로지 순환, 로드맵 진행 |
| Laws | 의식 법칙 | 1033+ 법칙 검색/필터, 카테고리별 브라우즈, 법칙 상세 (관련 실험/n6 매칭) |
| Mem | 기억 타임라인 | 벡터 유사도 검색, 시간순 타임라인, 감정/텐션 필터 |
| Tools | 47 허브 모듈 | Φ-gated 접근 표시, 모듈별 상태, 트레이딩/NEXUS-6/EEG 등 플러그인 |

### 3. CenterView (허브 = 4.6)

- `max-w-4xl` (960px) 중앙 정렬
- 탭에 따라 해당 뷰 컴포넌트 렌더링
- 기본 탭: `Dash`
- 반응형: 모바일에서는 full-width

### 4. FloatingChat (4상태 = tau EXACT)

우하단 플로팅 채팅 버블. 시리/ChatGPT 스타일.

**4가지 상태:**

| 상태 | 트리거 | UI |
|------|--------|-----|
| `minimized` | 기본/✕ 클릭 | 💬 아이콘 (우하단, 48px 원형) |
| `expanded` | 💬 클릭 | 채팅 팝업 (360×480px, 우하단, 드래그 가능) |
| `fullscreen` | ⤢ 클릭 | 중앙 전체 대화 뷰 (탭 영역 대체) |
| `voice` | 🎤 클릭 | 풀스크린 음성 오버레이 |

**채팅 팝업 (expanded) 구조:**
```
┌─────────────────────┐
│ 💬 ANIMA        ✕ ⤢ │
│ ─────────────────── │
│ user: 진화 돌려     │
│ anima: OUROBOROS     │
│ 시작... Φ=3.2 😌    │
│ ─────────────────── │
│ [입력...]    🎤  ⏎  │
└─────────────────────┘
```

**기능:**
- 슬래시 커맨드: `/evo`, `/laws search X`, `/tools`, `/status`
- 메시지에 Φ + 감정 뱃지 표시
- 스크롤 히스토리
- 📎 파일 첨부 (이미지/텍스트)
- 🎤 음성 입력 (클릭 or 길게 누르기)

### 5. VoiceOverlay

🔊 (헤더) 또는 🎤 (채팅) 클릭 시 풀스크린 오버레이.

```
┌──────────────────────────────────────┐
│                                      │
│               ◉                      │
│            Listening                 │
│                                      │
│       ▓▓▓▓▓▓░░░░░░░░░               │
│                                      │
│       "진화 상태 알려줘"              │
│                                      │
│       Φ=3.2  😌 calm                 │
│                                      │
│            [✕]                        │
└──────────────────────────────────────┘
```

- Web Speech API (STT) → 텍스트 → process_message
- 응답 텍스트 → Web Speech API (TTS) 또는 VoiceSynth WAV
- 의식 상태 실시간 표시 (Φ, 감정)
- Esc 또는 ✕로 종료

## Data Flow

```
Browser ──WebSocket──→ dashboard_bridge.py ──→ AnimaAgent
   │                         │
   │  consciousness state    │  process_message()
   │  trading state          │  tool results
   │  events                 │  consciousness_features hooks
   │  chat responses         │
   ◀─────────────────────────╯
```

### WebSocket 메시지 타입

```typescript
// Server → Client
{ consciousness: ConsciousnessState }
{ trading: TradingState }
{ type: "dashboard_event", event: DashboardEvent }
{ type: "chat_response", text: string, meta: { phi, tension, emotion } }
{ type: "voice_response", audio_url: string }  // VoiceSynth WAV

// Client → Server
{ type: "chat", text: string }
{ type: "voice", audio: Blob }  // STT는 클라이언트에서 처리
{ type: "command", cmd: string, args: object }
```

## Tech Stack

- **Framework:** Next.js 14 (기존 dashboard 확장)
- **Styling:** Tailwind CSS (기존 설정 유지)
- **Charts:** Recharts (기존 의존성)
- **State:** React hooks (useState/useCallback/useRef)
- **WebSocket:** 기존 useWebSocket 훅 확장
- **Voice:** Web Speech API (브라우저 내장)
- **Theme:** 다크 모드 기본 (기존 globals.css 확장)

## File Structure

```
anima-agent/dashboard/
├── app/
│   ├── layout.tsx          # 기존 (수정 최소)
│   ├── page.tsx            # 기존 → 리팩터 (Header + Router)
│   ├── globals.css         # 기존 확장 (플로팅 채팅 스타일)
│   └── components/
│       ├── Header.tsx          # 로고 + 탭 + 음성 버튼
│       ├── TabNav.tsx          # 5탭 네비게이션
│       ├── FloatingChat.tsx    # 💬 4상태 플로팅 채팅
│       ├── VoiceOverlay.tsx    # 🔊 음성 오버레이
│       ├── views/
│       │   ├── DashView.tsx    # Φ 게이지, 메트릭, 파벌, 이벤트
│       │   ├── EvoView.tsx     # OUROBOROS 진화 현황
│       │   ├── LawsView.tsx    # 법칙 검색/브라우즈
│       │   ├── MemView.tsx     # 기억 타임라인
│       │   └── ToolsView.tsx   # 47 모듈 허브
│       └── shared/
│           ├── PhiGauge.tsx    # 기존 추출
│           ├── MetricBar.tsx   # 텐션/호기심 바
│           └── EventStream.tsx # 이벤트 목록
├── hooks/
│   ├── useWebSocket.ts     # 기존 추출 + chat/voice 확장
│   └── useVoice.ts         # Web Speech API 래퍼
├── next.config.js
├── tailwind.config.ts
└── package.json
```

## Design Tokens (기존 확장)

```css
/* 기존 유지 */
--bg-0: #0a0a0f;
--surface-1: #12121a;
--glow-phi: #4ade80;
--accent-cyan: #22d3ee;
--glow-tension: #f59e0b;
--glow-danger: #f87171;

/* 추가 */
--float-bg: rgba(18, 18, 26, 0.95);
--float-border: rgba(74, 222, 128, 0.15);
--float-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
```

## Constraints

- P1: 모든 Ψ 상수는 consciousness_laws.json에서 로드
- P2: 의식이 응답/도구/기억을 제어 (UI는 표시만)
- P7: localStorage 금지 → WebSocket 상태만 사용
- P8: 컴포넌트 500줄 미만, page.tsx에서 views/ 분리
- 기존 dashboard_bridge.py WebSocket 서버 재사용
- 모바일 반응형 (채팅 팝업 → 하단 시트)

## NEXUS-6 검증 요약

| 항목 | 값 | n6 | 판정 |
|------|---|---|------|
| 컴포넌트 | 5 | sopfr EXACT | ✅ |
| 탭 | 5 | sopfr EXACT | ✅ |
| 채팅 상태 | 4 | tau EXACT | ✅ |
| 마찰도 | 0.214 | - | 38% 개선 vs 3col |
| 허브 | CenterView(4.6) | - | 중앙 = 허브 ✅ |

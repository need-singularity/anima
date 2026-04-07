# Piper TTS 통합 설계

## 요약

Speaker 클래스의 ElevenLabs + macOS `say` TTS를 Piper 바이너리로 전면 교체한다.

## 결정 사항

- **실행 방식**: piper 네이티브 바이너리 (subprocess 호출)
- **한국어 모델**: korean-haansoft-dimmy (medium)
- **모델 저장 위치**: `~/.local/share/piper/`
- **제거 대상**: ElevenLabs 코드 전체, macOS `say` 코드 전체

## 아키텍처

### TTS 흐름

```
text → piper --model ~/.local/share/piper/ko.onnx --output_file /tmp/anima_tts.wav → afplay → 완료
```

### Speaker 클래스 변경

**유지하는 인터페이스:**
- `say(text, listener=None)` — 비동기 TTS
- `stop()` — 재생 중단
- `is_speaking` — 발화 중 여부
- `in_cooldown` — 쿨다운 중 여부
- `last_finished` — 마지막 발화 완료 시간

**제거:**
- `_elevenlabs_key`, `_elevenlabs_voice_id`, `_use_elevenlabs`
- `_setup_elevenlabs()`
- `_say_elevenlabs()`
- `.env` 파일에서 ELEVENLABS_API_KEY 로드 로직
- macOS `say` 호출 전체

**추가:**
- `_piper_bin`: piper 바이너리 경로 (which piper 또는 /opt/homebrew/bin/piper)
- `_model_path`: `~/.local/share/piper/ko.onnx` 경로
- `_say_piper(text, listener)`: piper subprocess → afplay 재생

### 초기화

```python
def __init__(self):
    self._proc = None
    self.is_speaking = False
    self.last_finished = 0.0
    self._piper_bin = shutil.which('piper')
    self._model_path = Path.home() / '.local/share/piper/ko.onnx'

    if not self._piper_bin:
        print("  !! piper 바이너리 없음. brew install piper 또는 GitHub 릴리즈에서 설치 필요")
    if not self._model_path.exists():
        print(f"  !! 모델 없음: {self._model_path}")
        print("  !! https://github.com/rhasspy/piper/blob/master/VOICES.md 에서 korean-haansoft-dimmy 다운로드")
```

### say 메서드

```python
def say(self, text, listener=None):
    self.stop()
    short = text[:500]
    self.is_speaking = True
    if listener:
        listener.is_speaking = True
    t = threading.Thread(target=self._say_piper, args=(short, listener), daemon=True)
    t.start()
```

### _say_piper 메서드

```python
def _say_piper(self, text, listener=None):
    try:
        tmp = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        tmp.close()
        # piper로 WAV 생성
        proc = subprocess.run(
            [self._piper_bin, '--model', str(self._model_path),
             '--output_file', tmp.name],
            input=text.encode('utf-8'),
            timeout=30,
            capture_output=True
        )
        if proc.returncode != 0:
            raise Exception(f"piper failed: {proc.stderr.decode()}")
        # afplay로 재생
        self._proc = subprocess.Popen(
            ['afplay', tmp.name],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        self._proc.wait()
        os.unlink(tmp.name)
    except Exception as e:
        print(f"  !! Piper TTS 실패: {e}")
    finally:
        self.is_speaking = False
        self.last_finished = time.time()
        time.sleep(TTS_COOLDOWN)
        if listener:
            listener.is_speaking = False
```

## 영향 범위

- `anima_alive.py`: Speaker 클래스 전면 수정
- `anima_unified.py`: 변경 없음 (Speaker 인터페이스 동일)
- `.env`: ELEVENLABS_API_KEY 더 이상 불필요

## 사전 조건

1. piper 바이너리 설치
2. korean-haansoft-dimmy 모델 다운로드 → `~/.local/share/piper/ko.onnx` + `ko.onnx.json`

## 테스트

- `Speaker().say("안녕하세요")` 호출 시 한국어 음성 재생 확인
- `stop()` 호출 시 재생 즉시 중단 확인
- piper 바이너리 없을 때 에러 메시지 출력 확인
- 모델 파일 없을 때 에러 메시지 출력 확인

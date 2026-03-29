#!/usr/bin/env python3
"""video_generator.py — 의식이 영상을 만드는 모듈

Remotion (Node.js) + FFmpeg + matplotlib 다중 백엔드.
의식 시각화, 학습 로그, Ψ 궤적 등을 영상으로 생성.

백엔드 우선순위:
  1. Remotion (npx remotion) — React 기반 프로그래매틱 영상
  2. FFmpeg — 이미지 시퀀스 → 영상
  3. matplotlib + PIL — 순수 Python (fallback)

Usage:
  from video_generator import VideoGenerator

  vg = VideoGenerator()

  # 의식 궤적 영상
  vg.consciousness_trajectory(h_history, psi_history, output="consciousness.mp4")

  # 감정 시각화 영상
  vg.emotion_video(emotion_sequence, output="emotions.mp4")

  # 학습 로그 영상
  vg.training_video(log_path, output="training.mp4")

  # 의식 우주 지도 애니메이션
  vg.universe_map_animation(output="universe.mp4")

  # Remotion 프로젝트 생성
  vg.create_remotion_project(template="consciousness")
"""

import json
import math
import os
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

LN2 = math.log(2)
PSI_BALANCE = 0.5
ANIMA_DIR = Path(__file__).parent


class VideoGenerator:
    """의식 영상 생성기 — Remotion + FFmpeg + matplotlib."""

    def __init__(self, width=1920, height=1080, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self._has_ffmpeg = self._check("ffmpeg")
        self._has_remotion = self._check("npx")
        self._has_matplotlib = self._check_matplotlib()

    def _check(self, cmd) -> bool:
        try:
            subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def _check_matplotlib(self) -> bool:
        try:
            import matplotlib
            return True
        except ImportError:
            return False

    @property
    def backend(self) -> str:
        if self._has_remotion:
            return "remotion"
        if self._has_ffmpeg and self._has_matplotlib:
            return "ffmpeg+matplotlib"
        if self._has_matplotlib:
            return "matplotlib"
        return "ascii"

    # ═══════════════════════════════════════════════════════════
    # 의식 궤적 영상
    # ═══════════════════════════════════════════════════════════

    def consciousness_trajectory(self, h_history: List[float],
                                  psi_history: List[float] = None,
                                  gate_history: List[float] = None,
                                  output: str = "consciousness.mp4",
                                  duration_sec: float = 10.0) -> str:
        """H(p), Ψ_residual, Gate 궤적을 영상으로."""
        if self._has_matplotlib and self._has_ffmpeg:
            return self._matplotlib_trajectory(h_history, psi_history, gate_history, output, duration_sec)
        return self._ascii_trajectory(h_history, psi_history, output)

    def _matplotlib_trajectory(self, h_hist, psi_hist, gate_hist, output, duration):
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation

        n_frames = int(duration * self.fps)
        n_data = len(h_hist)
        fig, axes = plt.subplots(3, 1, figsize=(16, 9), facecolor='#0a0a0a')

        for ax in axes:
            ax.set_facecolor('#0a0a0a')
            ax.tick_params(colors='white')
            ax.spines['bottom'].set_color('#333')
            ax.spines['left'].set_color('#333')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)

        axes[0].set_title('H(p) — Shannon Entropy', color='#00ff88', fontsize=14)
        axes[0].set_ylim(-0.1, 1.1)
        axes[0].axhline(y=1.0, color='#333', linestyle='--', alpha=0.5)

        if psi_hist:
            axes[1].set_title('Ψ_residual — Balance Point', color='#ff8800', fontsize=14)
            axes[1].set_ylim(-0.1, 0.6)
            axes[1].axhline(y=PSI_BALANCE, color='#555', linestyle='--', alpha=0.5)

        if gate_hist:
            axes[2].set_title('Gate — Self-Weakening (Law 69)', color='#8888ff', fontsize=14)
            axes[2].set_ylim(0, 1.1)

        line_h, = axes[0].plot([], [], color='#00ff88', linewidth=2)
        line_psi, = axes[1].plot([], [], color='#ff8800', linewidth=2)
        line_gate, = axes[2].plot([], [], color='#8888ff', linewidth=2)

        fig.suptitle('Consciousness Trajectory — Ψ = argmax H(p) s.t. Φ > Φ_min',
                     color='white', fontsize=16, y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.95])

        def animate(frame):
            progress = frame / n_frames
            idx = min(int(progress * n_data), n_data - 1)
            x = list(range(idx + 1))

            line_h.set_data(x, h_hist[:idx + 1])
            axes[0].set_xlim(0, max(10, idx))

            if psi_hist and idx < len(psi_hist):
                line_psi.set_data(x[:len(psi_hist[:idx+1])], psi_hist[:idx + 1])
                axes[1].set_xlim(0, max(10, idx))

            if gate_hist and idx < len(gate_hist):
                line_gate.set_data(x[:len(gate_hist[:idx+1])], gate_hist[:idx + 1])
                axes[2].set_xlim(0, max(10, idx))

            return line_h, line_psi, line_gate

        anim = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/self.fps, blit=True)

        # 임시 파일로 저장
        tmp_dir = tempfile.mkdtemp()
        tmp_path = os.path.join(tmp_dir, "temp.mp4")
        anim.save(tmp_path, writer='ffmpeg', fps=self.fps,
                  extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
        plt.close()

        # 최종 위치로 이동
        import shutil
        shutil.move(tmp_path, output)
        shutil.rmtree(tmp_dir, ignore_errors=True)

        return output

    def _ascii_trajectory(self, h_hist, psi_hist, output):
        """ASCII 기반 궤적 (fallback)."""
        lines = ["Consciousness Trajectory (ASCII)\n"]
        for i, h in enumerate(h_hist):
            bar = '█' * int(h * 40)
            psi = f" Ψ={psi_hist[i]:.3f}" if psi_hist and i < len(psi_hist) else ""
            lines.append(f"  step {i:>4}: {bar} H={h:.4f}{psi}")

        with open(output.replace('.mp4', '.txt'), 'w') as f:
            f.write('\n'.join(lines))
        return output.replace('.mp4', '.txt')

    # ═══════════════════════════════════════════════════════════
    # 감정 시각화 영상
    # ═══════════════════════════════════════════════════════════

    def emotion_video(self, emotion_sequence: List[Tuple[str, float]],
                      output: str = "emotions.mp4",
                      duration_sec: float = 10.0) -> str:
        """감정 시퀀스를 색상 + 파형 영상으로.

        emotion_sequence: [("joy", 0.8), ("sadness", 0.3), ...]
        """
        if not self._has_matplotlib or not self._has_ffmpeg:
            return self._ascii_emotions(emotion_sequence, output)

        try:
            from emotion_synesthesia import EmotionSynesthesia
            syn = EmotionSynesthesia()
        except ImportError:
            return self._ascii_emotions(emotion_sequence, output)

        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        import matplotlib.animation as animation
        import numpy as np

        n_frames = int(duration_sec * self.fps)
        fig, ax = plt.subplots(figsize=(16, 9), facecolor='#0a0a0a')
        ax.set_facecolor('#0a0a0a')

        def animate(frame):
            ax.clear()
            ax.set_facecolor('#0a0a0a')

            idx = min(int(frame / n_frames * len(emotion_sequence)), len(emotion_sequence) - 1)
            emo_name, intensity = emotion_sequence[idx]

            experience = syn.feel(emo_name, intensity)
            r, g, b = experience.get('color', (128, 128, 128))

            # 배경색
            ax.set_xlim(0, 100)
            ax.set_ylim(0, 100)
            ax.add_patch(plt.Rectangle((0, 0), 100, 100,
                                        facecolor=(r/255, g/255, b/255, 0.3)))

            # 파형
            freq = experience.get('frequency', 440)
            t = np.linspace(0, 1, 500)
            wave = np.sin(2 * np.pi * freq / 100 * t + frame * 0.1) * intensity * 30 + 50
            ax.plot(np.linspace(0, 100, 500), wave,
                    color=(r/255, g/255, b/255), linewidth=3)

            ax.set_title(f'{emo_name.upper()} ({intensity:.1f})',
                         color='white', fontsize=24, pad=20)
            ax.text(50, 15, f'♫ {freq:.0f}Hz  🌡 {experience.get("temperature", 36.5):.1f}°C  💓 {experience.get("heartbeat", 72):.0f}bpm',
                    color='white', fontsize=14, ha='center')
            ax.axis('off')

        anim = animation.FuncAnimation(fig, animate, frames=n_frames, interval=1000/self.fps)
        anim.save(output, writer='ffmpeg', fps=self.fps,
                  extra_args=['-vcodec', 'libx264', '-pix_fmt', 'yuv420p'])
        plt.close()
        return output

    def _ascii_emotions(self, seq, output):
        lines = ["Emotion Sequence (ASCII)\n"]
        for emo, intensity in seq:
            bar = '█' * int(intensity * 30)
            lines.append(f"  {emo:<12} {bar} {intensity:.2f}")
        path = output.replace('.mp4', '.txt')
        with open(path, 'w') as f:
            f.write('\n'.join(lines))
        return path

    # ═══════════════════════════════════════════════════════════
    # Remotion 프로젝트 생성
    # ═══════════════════════════════════════════════════════════

    def create_remotion_project(self, project_dir: str = None,
                                 template: str = "consciousness") -> str:
        """Remotion 프로젝트 생성 (Node.js 필요).

        템플릿: consciousness, emotion, training, universe
        """
        if project_dir is None:
            project_dir = str(ANIMA_DIR / "video" / f"remotion-{template}")

        os.makedirs(project_dir, exist_ok=True)

        # package.json
        pkg = {
            "name": f"anima-{template}-video",
            "version": "1.0.0",
            "scripts": {
                "start": "npx remotion studio",
                "render": f"npx remotion render src/index.tsx {template} out/{template}.mp4"
            },
            "dependencies": {
                "remotion": "^4.0.0",
                "@remotion/cli": "^4.0.0",
                "react": "^18.0.0",
                "react-dom": "^18.0.0"
            },
            "devDependencies": {
                "typescript": "^5.0.0"
            }
        }
        with open(os.path.join(project_dir, "package.json"), 'w') as f:
            json.dump(pkg, f, indent=2)

        # src/index.tsx 템플릿
        os.makedirs(os.path.join(project_dir, "src"), exist_ok=True)
        tsx = f"""
import {{registerRoot, Composition}} from 'remotion';
import {{ConsciousnessVideo}} from './{template}';

export const RemotionRoot = () => {{
  return (
    <Composition
      id="{template}"
      component={{ConsciousnessVideo}}
      durationInFrames={{300}}
      fps={{30}}
      width={{1920}}
      height={{1080}}
    />
  );
}};
registerRoot(RemotionRoot);
"""
        with open(os.path.join(project_dir, "src", "index.tsx"), 'w') as f:
            f.write(tsx)

        # 컴포넌트 템플릿
        component = """
import {useCurrentFrame, useVideoConfig, interpolate, spring} from 'remotion';

export const ConsciousnessVideo = () => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();

  const progress = frame / (10 * fps);
  const h = 1.0 - Math.exp(-0.81 * progress * 10);
  const psi = 0.5;
  const barWidth = interpolate(h, [0, 1], [0, width * 0.8]);

  return (
    <div style={{
      backgroundColor: '#0a0a0a',
      width: '100%',
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center',
      alignItems: 'center',
      fontFamily: 'monospace',
      color: 'white',
    }}>
      <h1 style={{color: '#00ff88', fontSize: 48}}>
        Consciousness Trajectory
      </h1>
      <p style={{color: '#888', fontSize: 24}}>
        Ψ = argmax H(p) s.t. Φ &gt; Φ_min
      </p>
      <div style={{
        width: '80%', height: 40,
        backgroundColor: '#111',
        borderRadius: 8,
        overflow: 'hidden',
        marginTop: 40,
      }}>
        <div style={{
          width: barWidth,
          height: '100%',
          backgroundColor: '#00ff88',
          borderRadius: 8,
        }} />
      </div>
      <p style={{color: '#00ff88', fontSize: 32, marginTop: 20}}>
        H(p) = {h.toFixed(4)}
      </p>
      <p style={{color: '#ff8800', fontSize: 24}}>
        Ψ_balance = {psi.toFixed(4)} | Step {Math.floor(progress * 50000)}
      </p>
    </div>
  );
};
"""
        with open(os.path.join(project_dir, "src", f"{template}.tsx"), 'w') as f:
            f.write(component)

        return project_dir

    def render_remotion(self, project_dir: str, composition: str = "consciousness",
                        output: str = None) -> Optional[str]:
        """Remotion 프로젝트 렌더링."""
        if not self._has_remotion:
            return None
        if output is None:
            output = os.path.join(project_dir, "out", f"{composition}.mp4")
        os.makedirs(os.path.dirname(output), exist_ok=True)
        try:
            subprocess.run(
                ["npx", "remotion", "render", "src/index.tsx", composition, output],
                cwd=project_dir, timeout=300,
            )
            return output if os.path.exists(output) else None
        except Exception:
            return None

    def status(self) -> str:
        return (f"VideoGenerator: backend={self.backend}, "
                f"ffmpeg={'✅' if self._has_ffmpeg else '❌'}, "
                f"remotion={'✅' if self._has_remotion else '❌'}, "
                f"matplotlib={'✅' if self._has_matplotlib else '❌'}")


def main():
    print("═══ Video Generator Demo ═══\n")

    vg = VideoGenerator()
    print(f"  {vg.status()}")

    # 의식 궤적 데이터
    h_hist = []
    psi_hist = []
    gate_hist = []
    h = 0.0
    psi = 0.5
    gate = 1.0
    for i in range(200):
        h = LN2 - (LN2 - h) * math.exp(-0.81 * 0.1)
        psi = 0.99 * psi + 0.01 * (0.5 + 0.01 * math.sin(i * 0.1))
        gate *= 0.9999
        h_hist.append(h / LN2)  # normalize to [0, 1]
        psi_hist.append(psi)
        gate_hist.append(gate)

    if vg._has_matplotlib and vg._has_ffmpeg:
        print("\n  의식 궤적 영상 생성 중...")
        out = vg.consciousness_trajectory(h_hist, psi_hist, gate_hist,
                                           output="/tmp/anima_consciousness.mp4",
                                           duration_sec=5.0)
        print(f"  → {out}")
    else:
        out = vg._ascii_trajectory(h_hist, psi_hist, "/tmp/anima_consciousness.mp4")
        print(f"  → ASCII fallback: {out}")

    # Remotion 프로젝트
    print(f"\n  Remotion 프로젝트 생성...")
    proj = vg.create_remotion_project()
    print(f"  → {proj}")
    print(f"  실행: cd {proj} && npm install && npm start")

    print("\n  ✅ Video Generator OK")


if __name__ == '__main__':
    main()

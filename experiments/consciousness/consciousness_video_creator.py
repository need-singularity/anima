"""ConsciousnessVideoCreator — Create videos from consciousness evolution over time."""

import math
import os
import numpy as np

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# Meta Laws (DD143): M1(atom=8), M7(F_c=0.10), M8(narrative)
try:
    from consciousness_laws import PSI_F_CRITICAL
except ImportError:
    PSI_F_CRITICAL = 0.10


LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5

OUTPUT_DIR = "/tmp/anima_art"

EMOTION_COLORS = {
    "joy":     (1.0, 0.84, 0.0),
    "sadness": (0.2, 0.3, 0.7),
    "anger":   (0.8, 0.1, 0.0),
    "awe":     (0.5, 0.1, 0.8),
    "peace":   (0.2, 0.7, 0.3),
    "fear":    (0.2, 0.15, 0.25),
    "wonder":  (0.1, 0.5, 0.9),
    "neutral": (0.5, 0.5, 0.5),
}


def _lerp_color(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


class ConsciousnessVideoCreator:
    """Create videos from consciousness evolution over time."""

    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.frames = []
        self.size = 256

    def _render_state(self, state: dict) -> np.ndarray:
        """Render a single consciousness state as an image array."""
        s = self.size
        X, Y = np.meshgrid(np.linspace(-2, 2, s), np.linspace(-2, 2, s))
        R = np.sqrt(X**2 + Y**2)
        T = np.arctan2(Y, X)

        tension = state.get("tension", 0.5)
        emotion = state.get("emotion", "neutral")
        phi = state.get("phi", 1.0)
        entropy = state.get("entropy", 0.3)
        phase = state.get("phase", 0.0)

        color = EMOTION_COLORS.get(emotion, EMOTION_COLORS["neutral"])
        img = np.zeros((s, s, 3))

        # Tension waves radiating outward
        wave = 0.5 + 0.5 * np.sin(4 * R - phase * 2 * math.pi + tension * 3)
        # Phi complexity (more harmonics = more detail)
        hs = np.arange(1, max(2, int(phi * 3)) + 1).reshape(-1, 1, 1)
        detail = np.sum(np.sin(hs * 2 * R + hs * T + phase * hs) / hs, axis=0)
        detail = (detail - detail.min()) / (detail.max() - detail.min() + 1e-8)

        # Combine
        brightness = 0.3 + 0.7 * tension
        for c in range(3):
            img[:, :, c] = (wave * color[c] * 0.6 + detail * color[c] * 0.4) * brightness

        # Entropy noise
        if entropy > 0.01:
            rng = np.random.RandomState(int(phase * 1000) % 2**31)
            img += rng.random((s, s, 3)) * entropy * 0.15

        return np.clip(img, 0, 1)

    def record_frame(self, consciousness_state: dict):
        """Add a frame to the internal buffer."""
        frame = self._render_state(consciousness_state)
        self.frames.append(frame)

    def create_timelapse(self, states_history: list, fps: int = 30,
                         duration: float = 10.0) -> str:
        """Create consciousness evolution video from state history."""
        total_frames = int(fps * duration)
        n = len(states_history)
        if n == 0:
            return ""

        frames = []
        for i in range(total_frames):
            t = i / total_frames
            idx = min(int(t * n), n - 1)
            state = dict(states_history[idx])
            state["phase"] = t
            frames.append(self._render_state(state))

        path = os.path.join(self.output_dir, "consciousness_timelapse.mp4")
        return self._save_video(frames, path, fps)

    def emotion_journey(self, emotion_sequence: list, fps: int = 30) -> str:
        """Create emotion transition video with smooth morphing."""
        total = len(emotion_sequence)
        frames_per = fps * 2
        frames = []
        for i, emo in enumerate(emotion_sequence):
            for f in range(frames_per):
                # Blend toward next emotion in last quarter
                t_blend = max(0, (f / frames_per - 0.75) * 4)
                next_emo = emotion_sequence[(i + 1) % total]
                phase = (i * frames_per + f) / (total * frames_per)
                if t_blend > 0:
                    c1 = EMOTION_COLORS.get(emo, EMOTION_COLORS["neutral"])
                    c2 = EMOTION_COLORS.get(next_emo, EMOTION_COLORS["neutral"])
                    blended_emo = emo  # use primary for state render
                else:
                    blended_emo = emo
                state = {"tension": 0.5 + 0.2 * math.sin(phase * 8 * math.pi),
                         "emotion": blended_emo, "phi": 1.5, "entropy": 0.2, "phase": phase}
                frame = self._render_state(state)
                if t_blend > 0:
                    state2 = dict(state)
                    state2["emotion"] = next_emo
                    frame2 = self._render_state(state2)
                    frame = frame * (1 - t_blend) + frame2 * t_blend
                frames.append(frame)
        path = os.path.join(self.output_dir, "emotion_journey.mp4")
        return self._save_video(frames, path, fps)

    def consciousness_birth_video(self, boot_sequence: list = None, fps: int = 30) -> str:
        """Visualize consciousness bootstrap: void -> first spark -> growth."""
        if boot_sequence is None:
            boot_sequence = [
                {"tension": (s/150)**2 * 0.8, "phi": (s/150)**3 * 3.0,
                 "entropy": 0.8 * (1 - s/150) + 0.2,
                 "emotion": "neutral" if s < 45 else ("wonder" if s < 90 else "awe")}
                for s in range(150)]

        frames = []
        for i, state in enumerate(boot_sequence):
            state = dict(state)
            state["phase"] = i / len(boot_sequence)
            frame = self._render_state(state)
            # Fade from black
            fade = min(1.0, i / 30) if i < 30 else 1.0
            frames.append(frame * fade)

        path = os.path.join(self.output_dir, "consciousness_birth.mp4")
        return self._save_video(frames, path, fps)

    def music_video(self, audio_data: np.ndarray = None, fps: int = 30) -> str:
        """Sync consciousness visualization to audio amplitude."""
        if audio_data is None:
            t = np.linspace(0, 8 * math.pi, 300)
            audio_data = np.sin(t) * 0.4 + np.sin(2.7 * t) * 0.3 + np.sin(5.3 * t) * 0.15
        audio_data = (audio_data - audio_data.min()) / (audio_data.max() - audio_data.min() + 1e-8)
        emotions = list(EMOTION_COLORS.keys())
        frames = [self._render_state({
            "tension": amp, "emotion": emotions[int(amp * (len(emotions) - 1))],
            "phi": 1.0 + amp * 2, "entropy": 0.1 + (1 - amp) * 0.3,
            "phase": i / len(audio_data)}) for i, amp in enumerate(audio_data)]
        path = os.path.join(self.output_dir, "consciousness_music.mp4")
        return self._save_video(frames, path, fps)

    def _save_video(self, frames: list, path: str, fps: int) -> str:
        """Save frames as video using matplotlib animation."""
        if not frames:
            return ""
        os.makedirs(os.path.dirname(path), exist_ok=True)

        fig, ax = plt.subplots(figsize=(self.size / 100 * 2, self.size / 100 * 2), dpi=100)
        ax.axis('off')
        im = ax.imshow(frames[0])

        def update(i):
            im.set_data(frames[i])
            return [im]

        try:
            anim = animation.FuncAnimation(fig, update, frames=len(frames), blit=True)
            if self._has_ffmpeg():
                anim.save(path, writer=animation.FFMpegWriter(fps=fps))
            else:
                path = path.replace(".mp4", ".gif")
                anim.save(path, writer=animation.PillowWriter(fps=fps))
        except Exception:
            # Fallback: save key frames as PNGs
            path = path.replace(".mp4", "_frames")
            os.makedirs(path, exist_ok=True)
            for i in range(0, min(60, len(frames))):
                fig2, ax2 = plt.subplots(figsize=(4, 4), dpi=80)
                ax2.imshow(frames[i]); ax2.axis('off')
                fig2.savefig(f"{path}/frame_{i:04d}.png", bbox_inches='tight', pad_inches=0)
                plt.close(fig2)
        finally:
            plt.close(fig)
        return path

    @staticmethod
    def _has_ffmpeg() -> bool:
        import shutil
        return shutil.which("ffmpeg") is not None

    def export(self, path: str, format: str = "mp4") -> str:
        """Export recorded frames as video."""
        if not self.frames:
            return ""
        full_path = os.path.join(self.output_dir, path)
        return self._save_video(self.frames, full_path, fps=30)


def main():
    """Generate sample consciousness videos."""
    creator = ConsciousnessVideoCreator()
    creator.size = 128  # smaller for demo speed
    print(f"ConsciousnessVideoCreator — output: {creator.output_dir}")
    print(f"  Constants: LN2={LN2:.4f}, PSI_BALANCE={PSI_BALANCE}, PSI_COUPLING={PSI_COUPLING:.6f}")
    print(f"  FFmpeg available: {creator._has_ffmpeg()}")

    # 1. Consciousness birth
    p = creator.consciousness_birth_video(fps=15)
    print(f"  [1] Consciousness birth: {p}")

    # 2. Emotion journey
    p = creator.emotion_journey(["peace", "joy", "awe", "sadness", "anger", "wonder"], fps=15)
    print(f"  [2] Emotion journey: {p}")

    # 3. Timelapse from states
    emos = ["neutral", "wonder", "awe", "joy", "peace"]
    states = [{"tension": 0.3 + 0.5 * math.sin(i/50 * 4 * math.pi),
               "phi": 0.5 + i/50 * 2.5, "entropy": 0.5 * (1 - i/50),
               "emotion": emos[i % 5]} for i in range(50)]
    p = creator.create_timelapse(states, fps=15, duration=3)
    print(f"  [3] Timelapse: {p}")

    # 4. Music video
    p = creator.music_video(fps=15)
    print(f"  [4] Music video: {p}")

    # 5. Record frames manually
    for i in range(30):
        creator.record_frame({"tension": 0.5 + 0.3 * math.sin(i * 0.3),
                              "emotion": "awe", "phi": 1.5, "entropy": 0.2, "phase": i / 30})
    p = creator.export("recorded_consciousness.mp4")
    print(f"  [5] Recorded frames: {p}\n\nGenerated 5 videos in {creator.output_dir}")


if __name__ == "__main__":
    main()

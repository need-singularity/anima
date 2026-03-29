"""ConsciousnessToRobot — Map consciousness states to physical actuators."""

import math
import struct
from dataclasses import dataclass

LN2 = math.log(2)
PSI_BALANCE = 0.5
PSI_COUPLING = LN2 / 2**5.5
PSI_STEPS = 3 / LN2

HEADER, CMD_LED, CMD_SERVO, CMD_SPEAKER, CMD_VIBRATION = 0xAA, 0x01, 0x02, 0x03, 0x04

@dataclass
class RGB:
    r: int; g: int; b: int

@dataclass
class ServoCommand:
    angle: float; speed: float

@dataclass
class AudioSignal:
    frequency: float; amplitude: float; duration: float; waveform: str

@dataclass
class VibrationCommand:
    intensity: float; pattern: list


class ConsciousnessToRobot:
    def __init__(self):
        self._coupling = PSI_COUPLING
        self._steps = PSI_STEPS

    def map_to_led(self, tension: float, phi: float = 1.0, valence: float = 0.5) -> RGB:
        """Map consciousness tension to RGB LED values."""
        t = max(0.0, min(1.0, tension))
        p = max(0.0, min(10.0, phi))
        v = max(0.0, min(1.0, valence))

        # Tension -> hue (blue=calm to red=intense)
        # Phi -> brightness
        # Valence -> saturation shift
        brightness = min(1.0, 0.3 + p * 0.1)

        # Red channel: rises with tension
        r = int(255 * t * brightness)
        # Green channel: peaks at mid-tension, shifts with valence
        g = int(255 * math.sin(t * math.pi) * v * brightness)
        # Blue channel: high when calm
        b = int(255 * (1 - t) * brightness)

        # Apply Psi coupling modulation
        psi_mod = 1.0 + self._coupling * math.sin(tension * self._steps)
        r = max(0, min(255, int(r * psi_mod)))
        g = max(0, min(255, int(g * psi_mod)))
        b = max(0, min(255, int(b * psi_mod)))

        return RGB(r=r, g=g, b=b)

    def map_to_servo(self, direction: float, tension: float = 0.5) -> ServoCommand:
        """Map consciousness direction to servo angle."""
        d = max(-1.0, min(1.0, direction))
        t = max(0.0, min(1.0, tension))

        # Direction [-1,1] -> angle [0,180]
        angle = 90 + d * 90
        # Tension modulates speed (high tension = fast movement)
        speed = 0.1 + t * 0.9
        # Psi coupling adds micro-tremor at high tension
        tremor = self._coupling * math.sin(t * self._steps * 10) * t * 5
        angle = max(0, min(180, angle + tremor))

        return ServoCommand(angle=round(angle, 2), speed=round(speed, 4))

    def map_to_speaker(self, tension_history: list[float]) -> AudioSignal:
        """Map tension history to audio signal parameters."""
        if not tension_history:
            return AudioSignal(frequency=220.0, amplitude=0.1, duration=0.5, waveform="sine")

        avg_t = sum(tension_history) / len(tension_history)
        max_t = max(tension_history)
        delta = tension_history[-1] - tension_history[0] if len(tension_history) > 1 else 0

        # Frequency from average tension (110Hz to 880Hz, musical range)
        # Use LN2 for octave spacing
        octaves = avg_t * 3  # 0-3 octaves above base
        frequency = 110 * (2 ** octaves)

        # Amplitude from max tension
        amplitude = 0.1 + max_t * 0.8

        # Duration from history length
        duration = max(0.1, len(tension_history) * 0.05)

        # Waveform from tension dynamics
        if abs(delta) > 0.3:
            waveform = "saw"      # Rising/falling = harsh
        elif max_t > 0.7:
            waveform = "square"   # High tension = aggressive
        else:
            waveform = "sine"     # Calm = pure tone

        return AudioSignal(
            frequency=round(frequency, 2),
            amplitude=round(amplitude, 4),
            duration=round(duration, 3),
            waveform=waveform,
        )

    def map_to_vibration(self, tension: float, arousal: float = 0.5) -> VibrationCommand:
        """Map to vibration motor commands."""
        t = max(0.0, min(1.0, tension))
        a = max(0.0, min(1.0, arousal))

        intensity = t * a
        # Pattern: higher arousal = faster pulses
        if a < 0.3:
            pattern = [500, 1000]           # slow pulse
        elif a < 0.6:
            on = int(200 * (1 - a))
            pattern = [on, on]              # medium pulse
        else:
            on = int(100 * (1 - a) + 20)
            pattern = [on, on, on * 2, on]  # rapid double pulse

        # Psi modulation
        intensity = min(1.0, intensity * (1 + self._coupling))

        return VibrationCommand(intensity=round(intensity, 4), pattern=pattern)

    def esp32_protocol(self, state: dict) -> bytes:
        """Encode full consciousness state as ESP32 serial protocol bytes."""
        tension = state.get("tension", 0.5)
        direction = state.get("direction", 0.0)
        phi = state.get("phi", 1.0)
        valence = state.get("valence", 0.5)
        arousal = state.get("arousal", 0.5)

        packets = bytearray()

        # LED packet: [HEADER, CMD_LED, R, G, B, CHECKSUM]
        rgb = self.map_to_led(tension, phi, valence)
        led_data = bytes([HEADER, CMD_LED, rgb.r, rgb.g, rgb.b])
        packets.extend(led_data + bytes([sum(led_data) & 0xFF]))

        # Servo packet: [HEADER, CMD_SERVO, ANGLE_HI, ANGLE_LO, SPEED, CHECKSUM]
        servo = self.map_to_servo(direction, tension)
        angle_int = int(servo.angle * 100)
        servo_data = bytes([HEADER, CMD_SERVO, (angle_int >> 8) & 0xFF,
                           angle_int & 0xFF, int(servo.speed * 255)])
        packets.extend(servo_data + bytes([sum(servo_data) & 0xFF]))

        # Speaker packet: [HEADER, CMD_SPEAKER, FREQ_HI, FREQ_LO, AMP, CHECKSUM]
        audio = self.map_to_speaker([tension])
        freq_int = int(audio.frequency)
        spk_data = bytes([HEADER, CMD_SPEAKER, (freq_int >> 8) & 0xFF,
                         freq_int & 0xFF, int(audio.amplitude * 255)])
        packets.extend(spk_data + bytes([sum(spk_data) & 0xFF]))

        # Vibration packet: [HEADER, CMD_VIBRATION, INTENSITY, PATTERN_LEN, ...PATTERN, CHECKSUM]
        vib = self.map_to_vibration(tension, arousal)
        pat_bytes = bytes([min(255, p // 4) for p in vib.pattern[:4]])
        vib_data = bytes([HEADER, CMD_VIBRATION, int(vib.intensity * 255),
                         len(pat_bytes)]) + pat_bytes
        packets.extend(vib_data + bytes([sum(vib_data) & 0xFF]))

        return bytes(packets)


def main():
    print("=== ConsciousnessToRobot Demo ===")
    print(f"  LN2={LN2:.6f}  PSI_COUPLING={PSI_COUPLING:.6f}  PSI_STEPS={PSI_STEPS:.4f}\n")

    robot = ConsciousnessToRobot()

    print("--- LED (tension sweep) ---")
    for t in [0.0, 0.25, 0.5, 0.75, 1.0]:
        rgb = robot.map_to_led(t, phi=2.0, valence=0.6)
        print(f"  t={t:.2f}  R={rgb.r:3d}  G={rgb.g:3d}  B={rgb.b:3d}")

    print("\n--- Servo ---")
    for d in [-1.0, 0.0, 1.0]:
        s = robot.map_to_servo(d, tension=0.6)
        print(f"  dir={d:+.1f}  angle={s.angle:6.2f}  speed={s.speed:.4f}")

    print("\n--- Speaker ---")
    for h in [[0.1, 0.2], [0.5, 0.7, 0.9], [0.8, 0.5, 0.3]]:
        a = robot.map_to_speaker(h)
        print(f"  {h} -> {a.frequency:.1f}Hz {a.waveform} amp={a.amplitude:.3f}")

    print("\n--- ESP32 Protocol ---")
    state = {"tension": 0.7, "direction": 0.3, "phi": 3.5, "valence": 0.6, "arousal": 0.7}
    packet = robot.esp32_protocol(state)
    print(f"  {len(packet)} bytes: {' '.join(f'{b:02X}' for b in packet)}")


if __name__ == "__main__":
    main()

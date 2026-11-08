"""Capture a bounded utterance with ALSA; discard temporary audio after use."""
import subprocess
import tempfile
from pathlib import Path


class RecordingError(RuntimeError):
    pass


def record_utterance(duration: int = 5, device: str = "default") -> bytes:
    if not 1 <= duration <= 30:
        raise ValueError("Recording duration must be between 1 and 30 seconds")
    if not device or device.startswith("-") or len(device) > 128:
        raise ValueError("Invalid ALSA capture device")
    with tempfile.TemporaryDirectory(prefix="dogy-voice-") as directory:
        output = Path(directory) / "utterance.wav"
        try:
            subprocess.run(
                ["arecord", "-q", "-D", device, "-d", str(duration),
                 "-f", "S16_LE", "-r", "16000", "-c", "1", str(output)],
                check=True, timeout=duration + 10, capture_output=True,
            )
            return output.read_bytes()
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired, OSError) as exc:
            raise RecordingError("Microphone capture failed") from exc

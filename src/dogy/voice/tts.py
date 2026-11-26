"""Offline Piper synthesis and ALSA playback, with ephemeral audio files."""
from pathlib import Path
import subprocess
import tempfile


class SpeechError(RuntimeError):
    """Local speech synthesis or playback failed."""


def speak(text: str, model: Path, *, playback_device: str = "default",
          timeout: int = 90) -> None:
    """Synthesize text with a local Piper model and play the generated WAV."""
    if not text.strip():
        return
    if len(text) > 4000:
        raise ValueError("Speech output exceeds 4000 characters")
    model = Path(model).expanduser()
    if not model.is_file() or model.suffix != ".onnx":
        raise ValueError("A local Piper .onnx voice model is required")
    if not model.with_suffix(".onnx.json").is_file():
        raise ValueError("The matching Piper .onnx.json configuration is required")
    if not playback_device or playback_device.startswith("-") or len(playback_device) > 128:
        raise ValueError("Invalid ALSA playback device")
    with tempfile.TemporaryDirectory(prefix="dogy-tts-") as directory:
        wav_path = Path(directory) / "speech.wav"
        try:
            subprocess.run(
                ["piper", "--model", str(model), "--output_file", str(wav_path)],
                input=text, text=True, capture_output=True,
                check=True, timeout=timeout,
            )
            if not wav_path.is_file() or wav_path.stat().st_size == 0:
                raise SpeechError("Piper did not generate audio")
            subprocess.run(
                ["aplay", "-q", "-D", playback_device, str(wav_path)],
                capture_output=True, check=True, timeout=timeout,
            )
        except (FileNotFoundError, subprocess.CalledProcessError,
                subprocess.TimeoutExpired, OSError) as exc:
            raise SpeechError("Local speech synthesis or playback failed") from exc

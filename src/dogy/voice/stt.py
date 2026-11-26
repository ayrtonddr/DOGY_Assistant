"""Offline speech-to-text adapter using faster-whisper.

DOGY records PCM WAV at 16 kHz; decode it with the standard library to
avoid version-sensitive PyAV file decoding.
"""
import io
import wave

import numpy as np


class TranscriptionError(RuntimeError):
    pass


def decode_pcm_wav(audio: bytes) -> np.ndarray:
    """Return normalized mono 16-kHz float32 samples from a PCM WAV."""
    if not audio or len(audio) > 2_000_000:
        raise ValueError("Invalid audio payload")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                    wav.getcomptype()) != (1, 2, 16000, "NONE"):
                raise ValueError("Expected 16-kHz mono 16-bit PCM WAV")
            frames = wav.readframes(wav.getnframes())
        if not frames or len(frames) % 2:
            raise ValueError("Empty or invalid PCM samples")
        return np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    except (wave.Error, EOFError, OSError) as exc:
        raise ValueError("Invalid WAV recording") from exc


class WhisperTranscriber:
    def __init__(self, model_size: str = "tiny", language: str = "es"):
        if model_size not in {"tiny", "base", "small"}:
            raise ValueError("Unsupported Whisper model size")
        if language not in {"en", "es"}:
            raise ValueError("Unsupported language")
        self.language = language
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                model_size, device="cpu", compute_type="int8",
                local_files_only=True,
            )
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            raise TranscriptionError(
                "Whisper model unavailable locally; download it explicitly first"
            ) from exc

    def transcribe(self, audio: bytes) -> str:
        try:
            samples = decode_pcm_wav(audio)
            segments, _ = self.model.transcribe(
                samples, language=self.language, beam_size=1,
                vad_filter=False, condition_on_previous_text=False,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            raise TranscriptionError("Local transcription failed") from exc

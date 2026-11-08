"""Offline speech-to-text adapter using faster-whisper."""
import os
import tempfile
from pathlib import Path


class TranscriptionError(RuntimeError):
    pass


class WhisperTranscriber:
    def __init__(self, model_size: str = "tiny", language: str = "es"):
        if model_size not in {"tiny", "base", "small"}:
            raise ValueError("Unsupported Whisper model size")
        if language not in {"en", "es"}:
            raise ValueError("Unsupported language")
        self.language = language
        try:
            from faster_whisper import WhisperModel
            # After the first explicit model download, keep model resolution offline.
            self.model = WhisperModel(model_size, device="cpu", compute_type="int8",
                                      local_files_only=True)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            raise TranscriptionError(
                "Whisper model unavailable locally; download it explicitly first"
            ) from exc

    def transcribe(self, audio: bytes) -> str:
        if not audio or len(audio) > 2_000_000:
            raise ValueError("Invalid audio payload")
        fd, name = tempfile.mkstemp(prefix="dogy-stt-", suffix=".wav")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(audio)
            segments, _ = self.model.transcribe(
                name, language=self.language, beam_size=1,
                vad_filter=False, condition_on_previous_text=False,
            )
            return " ".join(segment.text.strip() for segment in segments).strip()
        except (OSError, RuntimeError, ValueError) as exc:
            raise TranscriptionError("Local transcription failed") from exc
        finally:
            Path(name).unlink(missing_ok=True)

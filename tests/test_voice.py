import io
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np
import pytest

from dogy.voice.record import record_utterance, RecordingError
from dogy.voice.stt import WhisperTranscriber, TranscriptionError, decode_pcm_wav


def make_wav(rate=16000, channels=1, width=2):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(width)
        output.setframerate(rate)
        output.writeframes(b"\x00\x00" * 160)
    return stream.getvalue()


def test_record_bounded():
    with pytest.raises(ValueError):
        record_utterance(duration=31)


def test_record_uses_alsa_without_shell():
    def fake_run(args, **kwargs):
        assert args[0] == "arecord"
        assert kwargs["check"] is True
        assert kwargs["timeout"] == 15
        assert "-r" in args and "16000" in args
        Path(args[-1]).write_bytes(make_wav())
    with patch("dogy.voice.record.subprocess.run", side_effect=fake_run):
        assert record_utterance() == make_wav()


def test_record_error_is_generic():
    with patch("dogy.voice.record.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RecordingError):
            record_utterance()


def test_pcm_decode_is_float32():
    samples = decode_pcm_wav(make_wav())
    assert samples.dtype == np.float32
    assert samples.shape == (160,)
    assert np.all(samples == 0)


@pytest.mark.parametrize("audio", [b"", b"bad", make_wav(rate=8000), make_wav(channels=2)])
def test_invalid_audio(audio):
    with pytest.raises(ValueError):
        decode_pcm_wav(audio)


def test_transcribe_uses_array_not_pyav():
    transcriber = object.__new__(WhisperTranscriber)
    transcriber.language = "es"
    def fake_transcribe(samples, **kwargs):
        assert isinstance(samples, np.ndarray)
        assert kwargs["language"] == "es"
        return iter([SimpleNamespace(text=" Hola "), SimpleNamespace(text=" DOGY ")]), None
    transcriber.model = SimpleNamespace(transcribe=fake_transcribe)
    assert transcriber.transcribe(make_wav()) == "Hola DOGY"


def test_reject_empty_audio():
    transcriber = object.__new__(WhisperTranscriber)
    with pytest.raises(TranscriptionError):
        transcriber.transcribe(b"")

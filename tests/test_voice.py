from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import pytest

from dogy.voice.record import record_utterance, RecordingError
from dogy.voice.stt import WhisperTranscriber


def test_record_bounded():
    with pytest.raises(ValueError):
        record_utterance(duration=31)


def test_record_uses_alsa_without_shell():
    def fake_run(args, **kwargs):
        assert args[0] == "arecord"
        assert kwargs["check"] is True
        assert kwargs["timeout"] == 15
        assert "-r" in args and "16000" in args
        Path(args[-1]).write_bytes(b"RIFFtest")
    with patch("dogy.voice.record.subprocess.run", side_effect=fake_run):
        assert record_utterance() == b"RIFFtest"


def test_record_error_is_generic():
    with patch("dogy.voice.record.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RecordingError):
            record_utterance()


def test_transcribe_and_cleanup():
    transcriber = object.__new__(WhisperTranscriber)
    transcriber.language = "es"
    seen = []
    def fake_transcribe(path, **kwargs):
        seen.append(path)
        assert Path(path).exists()
        assert kwargs["language"] == "es"
        return iter([SimpleNamespace(text=" Hola "), SimpleNamespace(text=" DOGY ")]), None
    transcriber.model = SimpleNamespace(transcribe=fake_transcribe)
    assert transcriber.transcribe(b"RIFFtest") == "Hola DOGY"
    assert not Path(seen[0]).exists()


def test_reject_empty_audio():
    transcriber = object.__new__(WhisperTranscriber)
    with pytest.raises(ValueError):
        transcriber.transcribe(b"")

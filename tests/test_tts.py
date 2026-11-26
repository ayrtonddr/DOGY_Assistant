from pathlib import Path
from unittest.mock import patch

import pytest

from dogy.voice.tts import SpeechError, speak


def test_speak_requires_local_model(tmp_path):
    with pytest.raises(ValueError, match="local Piper"):
        speak("Hello", tmp_path / "missing.onnx")


def test_speak_requires_voice_config(tmp_path):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    with pytest.raises(ValueError, match="configuration"):
        speak("Hello", model)


def test_speak_generates_and_plays_then_deletes(tmp_path):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    model.with_suffix(".onnx.json").write_text("{}")
    paths = []

    def run(args, **kwargs):
        if args[0] == "piper":
            assert kwargs["input"] == "Hola"
            assert kwargs["text"] is True
            Path(args[-1]).write_bytes(b"RIFFaudio")
        else:
            assert args[:4] == ["aplay", "-q", "-D", "default"]
            assert Path(args[-1]).is_file()
            paths.append(Path(args[-1]))

    with patch("dogy.voice.tts.subprocess.run", side_effect=run) as mocked:
        speak("Hola", model)
        assert mocked.call_count == 2
    assert not paths[0].exists()


def test_speak_handles_missing_piper(tmp_path):
    model = tmp_path / "voice.onnx"
    model.write_bytes(b"model")
    model.with_suffix(".onnx.json").write_text("{}")
    with patch("dogy.voice.tts.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(SpeechError):
            speak("Hola", model)


def test_speak_skips_empty_text(tmp_path):
    speak("   ", tmp_path / "missing.onnx")

import io
import json
from unittest.mock import patch
import pytest

from dogy.llm.ollama import OllamaClient, OllamaError
from dogy.router import respond


def test_loopback_only():
    for endpoint in ("http://192.168.1.10:11434", "https://127.0.0.1:11434",
                     "http://localhost:11434", "http://127.0.0.1:11434/other"):
        with pytest.raises(ValueError):
            OllamaClient(endpoint=endpoint)


def test_generate():
    payload = json.dumps({"message": {"content": "Hola."}}).encode()
    with patch("dogy.llm.ollama.urlopen", return_value=io.BytesIO(payload)) as mocked:
        assert OllamaClient().generate("Hola", "es") == "Hola."
        request = mocked.call_args.args[0]
        body = json.loads(request.data)
        assert body["stream"] is False
        assert body["messages"][1]["content"] == "Hola"


def test_stream():
    events = b'{"message":{"content":"Ho"},"done":false}\n{"message":{"content":"la"},"done":false}\n{"done":true}\n'
    with patch("dogy.llm.ollama.urlopen", return_value=io.BytesIO(events)):
        assert "".join(OllamaClient().stream("Hola", "es")) == "Hola"


def test_failure_is_generic():
    with patch("dogy.llm.ollama.urlopen", side_effect=OSError("secret path")):
        with pytest.raises(OllamaError, match="Local Ollama inference failed"):
            OllamaClient().generate("Hello")


def test_rules_bypass_model():
    class FailModel:
        def generate(self, *args):
            raise AssertionError("model should not be invoked")

    assert respond("hola", "es", llm=FailModel()).route == "rules"


def test_unknown_routes_to_model():
    class FakeModel:
        def generate(self, prompt, language):
            assert language == "es"
            return "Respuesta breve."

    reply = respond("Explica la luna", "es", llm=FakeModel())
    assert reply.route == "llm"
    assert reply.text == "Respuesta breve."

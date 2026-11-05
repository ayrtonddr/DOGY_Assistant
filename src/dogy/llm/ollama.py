"""Local-only Ollama inference. This module has no tool or memory access."""
import ipaddress
import json
from dataclasses import dataclass
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


class OllamaError(RuntimeError):
    pass


SYSTEM_PROMPT = (
    "You are DOGY, a bilingual English-Spanish personal voice assistant. "
    "Reply in the user's language, concisely and conversationally. "
    "For simple questions, use no more than three sentences. "
    "Do not use lists unless requested. If uncertain, say so. "
    "You have no access to tools, private memory, or user accounts."
)


@dataclass(frozen=True)
class OllamaClient:
    model: str = "qwen2.5:3b"
    endpoint: str = "http://127.0.0.1:11434"
    timeout: float = 90.0
    max_tokens: int = 160

    def __post_init__(self) -> None:
        url = urlsplit(self.endpoint)
        try:
            address = ipaddress.ip_address(url.hostname or "")
        except ValueError as exc:
            raise ValueError("Ollama endpoint must use a numeric loopback IP") from exc
        if (url.scheme != "http" or not address.is_loopback or
                url.username is not None or url.password is not None or
                url.path not in ("", "/") or url.query or url.fragment or
                not 0 < self.timeout <= 300 or not 1 <= self.max_tokens <= 2048):
            raise ValueError("Invalid local Ollama configuration")

    def _request(self, prompt: str, language: str, streaming: bool) -> Request:
        if language not in ("en", "es"):
            raise ValueError("Unsupported language")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": streaming,
            "options": {"num_ctx": 2048, "num_predict": self.max_tokens, "temperature": 0},
        }
        return Request(
            self.endpoint.rstrip("/") + "/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

    def generate(self, prompt: str, language: str = "en") -> str:
        try:
            with urlopen(self._request(prompt, language, False), timeout=self.timeout) as response:
                result = json.load(response)
            return result["message"]["content"].strip()
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            raise OllamaError("Local Ollama inference failed") from exc

    def stream(self, prompt: str, language: str = "en") -> Iterator[str]:
        try:
            with urlopen(self._request(prompt, language, True), timeout=self.timeout) as response:
                for line in response:
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event.get("error"):
                        raise OllamaError("Ollama returned an inference error")
                    chunk = event.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if event.get("done"):
                        break
        except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as exc:
            raise OllamaError("Local Ollama streaming failed") from exc

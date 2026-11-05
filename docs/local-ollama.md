# DOGY local Ollama integration (experimental)

DOGY remains offline by default. To enable local inference, create a separate config file:

```toml
[assistant]
name = "DOGY"
language = "es"
cloud_enabled = false
network_inference_enabled = false
[security]
tools_enabled = false
family_accounts_enabled = false
[storage]
state_dir = "state"
[llm]
backend = "ollama"
model = "qwen2.5:3b"
endpoint = "http://127.0.0.1:11434"
timeout = 90
max_tokens = 160
```

Save this as `config/local-ollama.toml`, then run:

```bash
uv sync
uv run pytest -q
uv run dogy doctor --config config/local-ollama.toml
uv run dogy chat --lang es --config config/local-ollama.toml
```

The default configuration remains `backend = "disabled"`. Deterministic commands (greetings, time, help) bypass inference. Unknown utterances are sent to the local Ollama `/api/chat` endpoint. The client also exposes a streaming method for future voice integration; the CLI currently uses non-streaming generation.

**Security limitations:** Only numeric loopback HTTP endpoints are accepted; no LAN, cloud, tools, or family authentication. This is not yet appropriate for private family data. The existing audit system stores a SHA-256 of the utterance, which can be vulnerable to dictionary guessing. The current timeout is a per-network-operation timeout, not a strict total generation deadline.

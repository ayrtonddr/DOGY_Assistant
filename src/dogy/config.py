from pathlib import Path
import ipaddress
import tomllib
from urllib.parse import urlsplit

DEFAULT_CONFIG = Path(__file__).resolve().parents[2] / "config" / "default.toml"

class ConfigError(ValueError):
    pass

def load_config(path: Path | None = None) -> dict:
    with (path or DEFAULT_CONFIG).open("rb") as handle:
        cfg = tomllib.load(handle)
    if cfg.get("assistant", {}).get("cloud_enabled") is not False:
        raise ConfigError("Cloud is unsupported and must be disabled")
    if cfg.get("assistant", {}).get("network_inference_enabled") is not False:
        raise ConfigError("Network inference is not yet implemented")
    if cfg.get("security", {}).get("tools_enabled") is not False:
        raise ConfigError("Tool execution is not yet implemented")
    if cfg.get("security", {}).get("family_accounts_enabled") is not False:
        raise ConfigError("Family authentication is not yet implemented")
    llm = cfg.get("llm", {})
    if llm.get("backend") not in ("disabled", "ollama"):
        raise ConfigError("Only disabled or local Ollama backend is supported")
    if llm["backend"] == "ollama":
        from .llm.ollama import OllamaClient
        try:
            OllamaClient(
                model=llm.get("model", "qwen2.5:3b"),
                endpoint=llm.get("endpoint", "http://127.0.0.1:11434"),
                timeout=float(llm.get("timeout", 90)),
                max_tokens=int(llm.get("max_tokens", 160)),
            )
        except (ValueError, TypeError) as exc:
            raise ConfigError("Invalid local Ollama configuration") from exc
    return cfg

from pathlib import Path
import tomllib

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
    if cfg.get("llm", {}).get("backend") != "disabled":
        raise ConfigError("LLM backend is not yet implemented")
    return cfg

from pathlib import Path
import pytest
from dogy.config import load_config, ConfigError
from dogy.router import respond
from dogy.audit import append_event, verify

def test_bilingual():
    assert "DOGY" in respond("hola", "es").text
    assert "DOGY" in respond("hello", "en").text

def test_unknown_fails_safe():
    assert respond("send my email", "en").route == "unsupported"

def test_config_fails_closed(tmp_path):
    p = tmp_path / "unsafe.toml"
    p.write_text('[assistant]\ncloud_enabled = true\nnetwork_inference_enabled = false\n[security]\ntools_enabled = false\nfamily_accounts_enabled = false\n[llm]\nbackend = "disabled"\n')
    with pytest.raises(ConfigError):
        load_config(p)

def test_audit_detects_edit(tmp_path):
    p = tmp_path / "audit.jsonl"
    append_event(p, "test", {"count": 1})
    append_event(p, "test", {"count": 2})
    assert verify(p)[0]
    p.write_text(p.read_text().replace('"count": 1', '"count": 9'))
    assert not verify(p)[0]

.PHONY: install test doctor chat-es chat-en audit
install:
	python3 -m venv .venv
	.venv/bin/python -m pip install -e '.[dev]'
test:
	.venv/bin/python -m pytest -q
doctor:
	.venv/bin/dogy doctor
chat-en:
	.venv/bin/dogy chat --lang en --timezone America/Mexico_City
chat-es:
	.venv/bin/dogy chat --lang es --timezone America/Mexico_City
audit:
	.venv/bin/dogy verify-audit

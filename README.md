# DOGY — Local-first family assistant

**Status: first executable bootstrap (Phase 0 / early Phase 1), not a finished assistant.**

DOGY is being built for an Ubuntu ThinkPad T14 PoC, then a Raspberry Pi 5 (8 GB) assistant node with the T14 as a LAN-only inference server. English and Spanish. Custom orchestration and security policy, no third-party assistant platform as core.

## What works now
- Installable Python package and `dogy` CLI
- Offline, bilingual deterministic text commands: greeting, time, help
- TOML config that rejects cloud, network inference, tool execution, and family-auth flags until implemented
- Prototype hash-chained audit log (no full transcript)
- Automated tests, GitHub Actions CI, ThinkPad diagnostic script

## What does NOT work yet
- No login, family accounts, private memory, PWA, voice/STT/TTS, timers, tool runner, LLM inference, mTLS, or cloud.
- This is **not safe for private family data**. No authenticated API exists yet.
- Audit hashes detect edits within an existing chain, but do not prevent an attacker from rewriting or deleting the whole file. No signing or external anchor yet.
- Avoid sensitive utterances: short-message hashes can reveal content through guessing.
- Do not open network ports or use this as a home automation controller.

## Ubuntu quick start

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git make
# clone your GitHub repository, then:
cd dogy
make install
make test
make doctor
make chat-es  # or make chat-en
make audit
bash scripts/diagnose-thinkpad.sh
```

If cloning under a different folder name, change the `cd` command. Commands assume they are run from repository root. `state/` is gitignored; treat it as sensitive and never commit it.

## GitHub upload

Create an **empty private** repository named `dogy` in GitHub (do not pre-create README/license). In the extracted folder:

```bash
git init -b main
git add .
git commit -m "Bootstrap DOGY offline foundation"
git remote add origin git@github.com:YOUR_USERNAME/dogy.git
git push -u origin main
```

Requires SSH authentication configured with GitHub. HTTPS remote is an alternative. On ThinkPad: `git clone git@github.com:YOUR_USERNAME/dogy.git`.

## Next engineering milestones
1. Threat model and benchmark CPU/audio on T14.
2. Add local identity provider, HTTPS, and explicit family access control before private data.
3. Add voice adapters and push-to-talk prototype.
4. Add isolated T14 inference and authenticated Pi-to-T14 transport (WireGuard + mTLS).
5. Add secure tool registry, memory encryption, approvals, and security tests.
6. Port ARM64 assistant services to Raspberry Pi 5.

See `PLAN.md` for the complete design. Do not deploy as a family service until security milestones pass.

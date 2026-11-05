# DOGY — Secure Family AI Assistant: Design and Implementation Plan

Status: draft v0.4 (reconciled with DOGY Phase 1 requirements)
Languages: English and Spanish
Targets: PoC on Lenovo ThinkPad T14 Gen 1 (x86_64, Ubuntu) → production on Raspberry Pi 5 (8 GB, aarch64, Raspberry Pi OS)
Topology: Raspberry Pi 5 = family assistant device (audio, identity, policy, tools, memory, audit, web/PWA). T14 = LAN LLM inference server (no tools, no persistent memory). Cloud = disabled for initial release; optional future gateway on the Pi.
Users: family accounts with private-by-default profiles, child restrictions, and explicitly shared family resources.
Interfaces: bilingual voice and authenticated responsive web/PWA (mobile browser).

---

## 1. Principles

1. **Build it yourself.** No assistant platform (Alexa, Home Assistant, Rhasspy, LangChain, etc.) as the core. The orchestrator, tool registry, policy engine, memory, and audit log are our own code. Third-party code is limited to low-level components (audio I/O, speech models, crypto primitives) that are swappable behind our interfaces.
2. **Fully local initial release.** Every request is handled on-device or on the trusted LAN. Cloud calls are disabled by default, including automatic fallback; any future cloud capability is a separately approved feature.
3. **Least data out.** Anything sent to the cloud is minimised, redacted, logged, and allowed only by category.
4. **Deny by default.** Tools, data categories, and network hosts are off until explicitly enabled in config.
5. **Portable core.** Audio, STT, TTS, and LLM backends are adapters. The core logic must run unchanged on x86_64 and aarch64.
6. **Inference is separate from authority.** The LAN LLM server only generates text. It never executes tools, never holds memory or audit data, and never decides policy. The Pi (the assistant device) makes every decision that has consequences.

7. **Family privacy by default.** Each person has an independently authenticated account, private conversations and memory, and explicit shared-family spaces. A child profile has restricted tools and no administrative privileges.
8. **Companion confirmations.** Sensitive actions require a fresh authenticated approval in the web/PWA; voice recognition or a spoken PIN alone is not sufficient.

Note on "build it myself": we will not write our own cryptography or speech recognition. We build the parts that carry the security and product decisions (routing, policy, tools, memory, audit) and use vetted primitives for the rest.

---

## 2. Architecture

```
            ┌────────────── Device (T14 / Pi) ──────────────────────────┐
 Mic ─► Wake/PTT ─► VAD ─► STT (faster-whisper / whisper.cpp)           │
                              │ text + detected language (en/es)       │
                              ▼                                        │
                     ┌─ Router (on Pi) ─────────────────────┐           │
                     │  1. rules (Pi, no model)             │           │
                     │  2. LAN LLM (T14, mTLS over LAN) ────┼──► T14: llama.cpp / Ollama
                     │     unavailable? ─► step 3 or reply  │           │  (inference only)
                     │  3. cloud gateway OFF in initial release     │
                     └──────────────┬───────────────────────┘           │
                                    ▼                                   │
                     Identity + policy (family roles, ownership, risk) │
                                    ▼                                   │
                     Tool runner (sandboxed subprocesses)               │
                       timers · notes · calendar · web search · …      │
                                    ▼                                   │
                     Per-user encrypted SQLite · Audit (hash-chain)    │
                                    ▼                                   │
                     Reply text ─► TTS (Piper, es/en voice) ─► Speaker  │
            └────────────────────────────────────────────────────────────┘
```

Web/PWA clients connect over local HTTPS to the Pi-side API (or the T14 stand-in during development). The API authenticates each session and resolves the active user before retrieving context, invoking the router, or considering tools. Voice on a shared microphone is anonymous until the user authenticates via a companion session; anonymous voice is restricted to public/rules-only operations.

### Components

| Component | PoC (T14) | Pi | Notes |
|---|---|---|---|
| Audio capture/playback | PipeWire via `sounddevice` | ALSA, USB mic or ReSpeaker | Adapter interface |
| Push-to-talk (PoC) | Keyboard key via `evdev` | GPIO button | Wake word added in Phase 3 |
| Wake word | openWakeWord, custom "hey …" models | same | Train EN and ES phrases |
| VAD | Silero VAD (ONNX) | same | Ends utterance detection |
| STT | faster-whisper `small`, int8, CPU | faster-whisper `base` or whisper.cpp `tiny`/`base` | Auto-detects en/es |
| TTS | Piper: `en_US-*` and `es_ES-*`/`es_MX-*` | same | Voice chosen by reply language |
| Local LLM (inference) | T14 runs the model: Ollama or llama.cpp `llama-server`, 7–8B instruct (Qwen or Llama class, multilingual), quantised Q4/Q5 | Pi calls the T14 over LAN. Pi runs no model | Model size chosen by Phase 0 benchmark |
| LLM client | Pi's `llm/lan_client.py` (talks to T14 only) | same | Only the Pi holds the client credential |
| Cloud LLM | Disabled | Disabled | Future optional gateway only after explicit opt-in and security review |
| Storage | SQLite + SQLCipher (or vetted app-level AEAD encryption via `cryptography`) | same | Per-user ownership enforcement; encryption keys protected by OS credentials |
| Identity | Local OIDC provider or passkey-capable identity service | same | Adult/child/admin roles; no shared logins; local HTTPS required |
| Web/PWA | Responsive authenticated web app | Pi-hosted HTTPS | Personal chat, approvals, memory management, admin console |
| Config | TOML, validated with our own schema | same | No secrets in config files |

Model IDs for the cloud gateway are set in config, not hard-coded, so they can be changed without code edits.

---

## 3. LAN inference server (T14)

The T14 is the "brain" when you are home; the Pi is the "body" (microphone, speaker, tools, memory, audit).

**Role of the T14 server**
- Runs `llama-server` (llama.cpp) or Ollama bound to the LAN interface only. Exposes a minimal API: `POST /v1/chat` with messages and a JSON-schema constraint for tool calls, and `GET /health`.
- Stateless: no memory, no audit log, no tools. Each request carries its full context from the Pi.
- Serves one model at a time. Model name and quantisation are set in the T14's own config, not by the Pi.

**Network and authentication**
- Preferred link: WireGuard or Tailscale between Pi and T14, even on the home LAN. This keeps the server reachable from the Pi when the network changes and avoids exposing it to other LAN devices.
- Mutual TLS: each side has its own certificate, issued by a private CA you create. The T14 accepts only the Pi's client certificate. A bearer token is not enough on its own.
- Firewall: `ufw` (Ubuntu's default firewall front-end) on the T14 allows the inference port only from the Pi's WireGuard address. Default deny incoming: `ufw default deny incoming`.
- No port forwarding on the router. The server is never reachable from the internet.
- Certificates and keys live in the OS keyring (T14) and `systemd-creds` (Pi). Rotation procedure documented; certificates expire after 1 year.

**Reliability on a laptop**
- The T14 must stay reachable while you are home. On Ubuntu, set `HandleLidSwitch=ignore` and `HandleLidSwitchExternalPower=ignore` in `/etc/systemd/logind.conf` (or a drop-in under `/etc/systemd/logind.conf.d/`), and disable automatic suspend on AC in Settings → Power, otherwise the server sleeps when the desktop goes idle. Document the setting; it is a real limitation.
- Health check every 30 s from the Pi. If the T14 is down, the router drops to step 3 (cloud, if allowed) or replies "El servidor local no está disponible" / "The local server is unavailable".
- Wake-on-LAN is optional and depends on the T14's firmware. Do not rely on it for the PoC.
- A Raspberry Pi 5 as the server is not an option: it has no GPU, and the model would be too slow and too small to be useful. If you later want an always-on server, a mini PC is the better choice.

**Threat model for the LAN link**
- Assumed: another device on the LAN may be compromised. Mutual TLS and firewalling stop it from reaching the model or injecting into the Pi's context.
- The model's output is untrusted. The Pi validates every tool call (see §5), so a compromised or manipulated model cannot run a tool outside policy.
- Prompts sent to the T14 contain the user's private context. This is acceptable because the T14 is your machine, but it is logged only as lengths and hashes on the Pi side, not as full text.

**Performance expectations (to verify in Phase 0)**
- Expect CPU-only inference on the T14 (integrated graphics). Check the T14's RAM before choosing a model: 16 GB supports a Q4 7–8B model comfortably, 8 GB is tight.
- Measure time to first token and tokens per second for the chosen model, in both English and Spanish. These numbers decide whether the LAN path meets the < 3 s target in §11.

## 4. Local-first routing

Every utterance goes through this decision chain:

1. **Rules layer (on Pi, no model):** timers, "what time is it", unit conversion, simple arithmetic. Handled deterministically. Cost: zero, data leaves nothing.
2. **LAN LLM (T14):** intent classification, tool selection, summarisation of local data, general chat. Used when the T14 health check passes. Traffic stays on your own network.
3. **Optional future cloud escalation (not implemented or enabled in the initial release; only if all are true):**
   - The T14 is unavailable, or the LAN model reports low confidence, or fails schema validation twice, **or** the request is classed as "needs external knowledge or hard reasoning" by the user's allowed categories, and
   - the cloud category is enabled in config, and
   - daily budget (tokens and € cost) is not exhausted, and
   - the payload passes the redaction filter.

Users can force "solo local" / "local only" per request. A future "usa la nube" / "use cloud" request may only opt in for that turn when an administrator has separately enabled the cloud gateway and the current user/category is authorized; spoken instructions cannot override global cloud-off policy.

When a cloud call happens, the assistant says so in the reply language ("Lo he consultado en la nube") and logs it.

---

## 5. Optional future cloud gateway (disabled in MVP)

This section is a deferred design, not part of the initial fully local deployment. All cloud traffic, if explicitly enabled in a later release, must go through one module. Nothing else in the code imports the cloud SDK. Outbound firewall rules deny cloud endpoints by default.

**Outbound payload rules**
- Allowed categories are explicit in config: e.g. `general_knowledge: on`, `calendar: off`, `notes: off`, `contacts: off`.
- Redaction before send: emails, phone numbers, IBANs/card numbers, addresses, and API-key-looking strings are replaced with placeholders. Regex plus a tested list; this is best-effort and documented as such.
- Minimum context: current utterance plus at most N recent turns, no full memory dump.
- Tool outputs from private sources (calendar, notes) are **never** sent to cloud unless their category is on.

**Transport and keys**
- TLS only, certificate verification on, pinned hostname for the provider.
- API key stored in `systemd-creds` (Pi/Raspberry Pi OS, T14/Ubuntu 24.04+) or the system keyring. Read into memory at start, never logged, never in the repo.
- Retention: check and record the provider's current data-retention and training terms for the API plan you use. Do not assume them from memory.

**Controls**
- Daily budget caps (tokens and money), with a hard stop.
- Kill switch: one command or voice phrase ("desactiva la nube" / "disable cloud") disables cloud until re-enabled.
- Every cloud request is audit-logged: time, model, category, token counts, redaction hits, and a hash of the payload. The full payload is kept only in an encrypted debug log that is off by default.

**Injection defence for cloud answers**
- Cloud output is treated as untrusted text. It can propose tool calls, but the policy engine validates them the same way as local ones.

---

## 6. Policy and tools

**Risk tiers**

| Tier | Examples | Rule |
|---|---|---|
| 0 Read-only public | time, weather, web search | Runs freely |
| 1 Private read | read own notes, read own calendar | Requires authenticated user and record ownership; response remains local |
| 2 Reversible write | create personal timer, add own note | Requires authenticated user for persistent changes; runs and announces, undo where feasible |
| 3 External effect | send message, create calendar event for others | Requires authenticated companion confirmation and policy approval; child restrictions apply |
| 4 Forbidden by voice | unlock doors, payments, bulk deletion | Disabled by default; any later enabling requires dedicated companion flow and fresh re-authentication |

**Authorization contract**
- Derive user identity from a validated session, never from LLM text, voice identification, or a client-supplied user ID.
- Authorize every record read/write against the user, family workspace grants, role, age restrictions, and tool risk tier. Admin roles do not implicitly grant access to private conversations.
- Apply least-privilege service accounts and enforce ownership in the storage access layer; test cross-user access, enumeration, and shared-resource revocation.
- Voice without an authenticated companion session may only execute public, non-sensitive rules-layer actions.

**Tool contract**
- Each tool is a folder with a `manifest.toml`: name, description, risk tier, input JSON schema, data categories read/written, network hosts, and timeout.
- The model can only call tools in the registry. Arguments are validated against the schema before execution.
- Tools run as separate subprocesses under a dedicated low-privilege user, with a timeout and output size limit.
- Step limit per request (e.g. 5 tool calls) and rate limit per tool, to stop loops.

**Sandboxing**
- systemd unit per tool runner with `DynamicUser=yes`, `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `NoNewPrivileges=yes`, `RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX`, and `IPAddressAllow=` set from the manifest.
- On the PoC, if systemd-run is inconvenient, use a bubblewrap wrapper instead. Same policy either way.

---

## 7. Memory and data

- **Short-term:** last N turns in RAM only, partitioned by authenticated user/session; no cross-user context mixing.
- **Long-term:** explicit facts the authenticated user asks to save ("recuerda que…"). Stored encrypted in SQLite, tagged with immutable owner ID, category, creation date, and sharing scope.
- **Family shared memory:** separate workspace records with explicit access grants; no implicit sharing from private user memories.
- **Children:** configurable retention and guardian controls, with clear boundaries on guardian access to private content.
- **No raw audio stored.** Audio exists in memory for one utterance and is discarded.
- **Transcripts:** kept for 7 days by default, configurable, deletable by a single command.
- **Delete-all:** authenticated, scoped deletion of the requesting user’s memories/transcripts; shared records require appropriate workspace permission. Audit entries are retained according to a separate documented security retention policy and do not contain deleted plaintext.
- **Key management:** encryption-at-rest alone does not isolate users if one process holds all keys; application authorization and restricted service identities are mandatory. Backups are encrypted and restoration is tested.

---

## 8. Audit log

- Append-only JSON Lines file on the Pi. Each entry contains a SHA-256 of the previous entry, so accidental edits are detectable; a privileged attacker could rewrite the entire chain. Periodically anchor signed checkpoints to a separately protected location to improve tamper evidence.
- Logs include authenticated actor ID (or anonymous), authorization decision, target resource scope, and: wake/PTT events, STT result length (not text, unless debug), routing decision and reason, LAN LLM calls (endpoint, latency, prompt length and hash, no full text), cloud calls (see §5), every tool call with redacted arguments, confirmations, and errors.
- Secrets and redaction matches are never written in plain text.
- A `verify-audit` command checks the hash chain.

---

## 9. Bilingual design

- **STT:** Whisper auto-detects language. We also record the detected language and confidence, and reject low-confidence detections by asking the user to repeat.
- **Replies:** the LLM is instructed to answer in the language of the user's last utterance. Rules-layer responses use per-language string tables.
- **TTS:** voice is selected by reply language. Piper voices are installed for both.
- **Wake words:** one phrase per language, or one phrase that works in both. Decide after the PoC measures false triggers.
- **Tests:** a bilingual test corpus (about 100 utterances per language) covers intents, tool calls, and rules-layer replies. Measure accuracy in both languages separately.

---

## 10. Repository layout (planned)

```
dogy/
├── PLAN.md
├── pyproject.toml
├── config/
│   ├── default.toml          # no secrets; safe defaults (cloud off)
│   └── local.toml            # gitignored, per-device overrides
├── src/dogy/
│   ├── api/                  # local HTTPS-facing API and authenticated endpoints
│   ├── identity/             # local OIDC/passkeys, sessions, family roles
│   ├── family/               # ownership, sharing, guardian policy
│   ├── audio/                # capture, playback, PTT, wake word, VAD
│   ├── stt/                  # adapters
│   ├── tts/                  # adapters
│   ├── llm/                  # lan_client.py (Pi side), adapter interface
│   ├── inference_server/     # T14 side: llama-server/Ollama config, health, firewall/cert setup notes
│   ├── cloud/                # gateway, redaction, budget, kill switch  ← security boundary
│   ├── router.py
│   ├── policy.py
│   ├── tools/                # registry + runner (subprocess sandbox)
│   ├── memory/               # encrypted per-user and shared store
│   ├── audit/                # hash-chained log + verifier
│   ├── i18n/                 # en, es string tables
│   └── main.py
├── web/                      # responsive companion PWA
├── deployments/              # T14 PoC and Pi service definitions
├── tools/                    # built-in tools, each with manifest.toml
├── tests/
│   ├── unit/
│   ├── security/             # isolation, auth bypass, redaction, prompt injection
│   └── corpus/               # en and es utterances + expected intents
└── scripts/
    ├── setup-t14-inference.sh   # model server, firewall, client cert
    └── setup-pi.sh              # assistant device, client cert, systemd units
```

Use a `Makefile` or `just` for common tasks. Pin dependencies with hashes (`pip-compile --generate-hashes`), and run `pip-audit` in CI.

---

## 11. Phases and milestones

### Phase 0: Environment, threat model, and benchmarks (T14, 3–5 days)
- Ubuntu setup: Python 3.12 (default on Ubuntu 24.04; use the deadsnakes PPA on 22.04), llama.cpp or Ollama, Piper, faster-whisper, PipeWire check (default audio stack on Ubuntu 22.04+).
- Scripts use `apt` and are written to run on Ubuntu (T14) and Raspberry Pi OS (Pi), both Debian-based.
- Check T14 RAM and CPU model; verify CPU-only inference and measure thermal behavior.
- Create family threat model, repository scaffold, default-deny configuration, and synthetic test identities.
- Validate that no service listens on a public interface, and that no cloud inference traffic is possible.
- Benchmark on the T14: STT latency for `tiny`/`base`/`small` in en and es; LLM time-to-first-token and tokens/s for 3B, 7B, and 8B quantised models in en and es; TTS latency.
- **Exit:** a table of numbers that picks the model size for the LAN server.

### Phase 1: Secure identity, web skeleton, and push-to-talk voice loop (T14, 1–2 weeks)
- Local HTTPS and identity provider; adult, child, and administrator synthetic accounts; authenticated web/PWA skeleton.
- PTT key → record → VAD trim → STT → rules-layer reply → TTS → speaker. Anonymous voice remains limited to public commands.
- Bilingual rules responses (time, timer, unit conversion).
- Audit log and config loader from day one.
- **Exit:** 10 consecutive en and es commands work end to end, with latency logged; web login works; unauthorized access and cross-user record reads are rejected.

### Phase 2: LAN inference server and tool calling (T14 + T14 as Pi stand-in, 2–3 weeks)
- Set up the T14 inference server: `llama-server` or Ollama bound to the WireGuard interface, `ufw` rules, private CA, server certificate.
- Pi-side `lan_client.py` with client certificate, health check, timeout, and fallback path.
- Policy engine, tool registry, subprocess runner, family ownership and permission enforcement.
- First tools: timer, notes (local, encrypted memory), time, unit conversion.
- Bilingual system prompt and intent corpus.
- **Exit:** tool calls validate and run; invalid calls are rejected; the server refuses connections without a valid client cert; corpus accuracy reported per language.

### Phase 3: Family memory, companion approvals, and security tests (T14 + Pi stand-in, 2 weeks)
- Implement encrypted per-user memory, shared-family grants, retention and deletion.
- Implement authenticated web/PWA approval flow for tier-3 actions, and guardian restrictions.
- Keep cloud disabled; only document and test the future cloud gateway interface, redaction and budgets as deferred design.
- Security test suite: redaction tests, policy bypass attempts, prompt-injection cases (malicious web text trying to trigger tier 2+ tools), a test that proves no cloud call happens with cloud off, and a test that T14 down → safe local reply works with no cloud request.
- **Exit:** all security tests pass; a network capture during a "solo local" session shows zero outbound LLM traffic, and only LAN traffic to the T14.

### Phase 4: Wake word and polish (T14, 1–2 weeks)
- openWakeWord with custom "hey" phrases in en and es. Measure false triggers on about 1 hour of TV/music audio.
- Silero VAD for hands-free use.
- Memory commands, retention, delete-all, `verify-audit`.

### Phase 5: Port to Raspberry Pi 5 (8 GB) (1–2 weeks)
- Move the assistant device to the Pi: ALSA audio, GPIO button, smaller STT model, Piper voices, client certificate for the T14.
- The Pi runs no LLM. It calls the T14 over WireGuard/LAN. Test 8 GB memory pressure with STT, TTS, identity, API and database concurrently.
- Run the same test suite on aarch64. Measure latency on the Pi and tune.
- systemd service with `DynamicUser`, creds, and the tool sandbox.
- **Exit:** the same corpus and family authorization tests pass on aarch64; cloud remains disabled; the Pi behaves safely when the T14 is asleep.

### Phase 6: Hardening, family usability, and optional integrations
- Expand the existing companion web/PWA with audit viewing, per-user memory controls, family sharing, and passkey-based re-authentication.
- Remote access via WireGuard or Tailscale, not port forwarding.

---

## 12. Targets

| Metric | Target (T14 PoC) | Target (Pi 5 + T14 LAN LLM) |
|---|---|---|
| End of speech → start of reply, rules path | < 1 s | < 2 s |
| End of speech → start of reply, LAN LLM | < 3 s | < 4 s (includes LAN hop) |
| End of speech → start of reply, cloud | Not applicable: disabled | Not applicable: disabled |
| Corpus intent accuracy | ≥ 90% per language | ≥ 90% per language |
| False wake-word triggers | < 1 per hour of TV audio | same |
| Cloud calls when cloud is off | 0 | 0 |
| Unauthenticated connections accepted by T14 | 0 | 0 |
| Cross-user private resource access successes | 0 in test suite | 0 in test suite |
| Sensitive voice-only actions executed | 0 | 0 |
| Family web authentication | All protected endpoints | All protected endpoints |

---

## 13. Decisions

**Resolved**
- **Local LLM host:** the T14 is the LAN inference server. The Pi runs no model. (Decided by user.)
- **Languages:** English and Spanish.
- **Cloud:** disabled for initial release; future optional gateway requires explicit enablement and security review.
- **Project name:** DOGY.
- **Users:** family with private accounts, child restrictions, and explicitly shared resources.
- **Interfaces:** voice and authenticated responsive web/PWA.
- **Development host:** Ubuntu T14, CPU-only unless benchmark shows otherwise.
- **Target device:** Raspberry Pi 5, 8 GB, for voice, identity, policy, tools, memory and web; T14 remains the LAN inference server.

**Open**
1. **Future cloud provider:** deferred; do not choose or provision credentials in MVP.
2. **Wake word vs. push-to-talk:** keep PTT until the wake word is measured, or start with wake word in Phase 1? (Recommendation: PTT first.)
3. **Initial tools:** prioritize time, timers, and per-user notes; calendar/email/web integrations are deferred pending per-user permissions and credential review.
4. **Mic for the Pi:** USB mic, or a ReSpeaker-style array (better far-field pickup)?
5. **LAN link:** WireGuard (private, fully under your control) or Tailscale (easier, relies on a third-party coordination service)? (Recommendation: WireGuard for the PoC.)
6. **T14 always-on:** accept that the server is available only when the laptop is awake and plugged in, or invest in a mini PC later?

---

## 14. Assumptions recorded

- The T14 is running Ubuntu (24.04 recommended), with the laptop's built-in mic and speakers used for the PoC.
- The Pi runs Raspberry Pi OS (Debian-based).
- The assistant is for a family. Each member has an independent identity; children have restricted capabilities.
- The web/PWA works on mobile browsers; a native mobile app is not included in the initial release.
- Voice identity is not trusted for accessing private data without companion authentication.
- The wake word is a custom phrase, not Alexa or Google, to avoid licensing and privacy issues.
- Cloud is OFF in the initial release; the gateway is a deferred extension.
- Raspberry Pi 5 8 GB and T14 availability are planning assumptions to validate against actual hardware.

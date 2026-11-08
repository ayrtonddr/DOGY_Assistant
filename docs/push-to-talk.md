# DOGY push-to-talk voice prototype

This branch builds on `feature/local-ollama-inference` (PR #1), not `main`. It adds **voice input only**; DOGY still responds in text.

## ThinkPad setup

```bash
sudo apt install -y alsa-utils
uv sync --extra voice
# One-time explicit model download (requires internet):
uv run --extra voice python -c 'from faster_whisper import WhisperModel; WhisperModel("tiny", device="cpu", compute_type="int8")'
# Run with the existing opt-in local Ollama config:
uv run --extra voice dogy voice --lang es --record-seconds 5 --stt-model tiny --config config/local-ollama.toml
```

Press Enter to start a five-second recording, speak in Spanish, and wait for transcription. DOGY prints the recognized text and streams its response. Type `exit` to quit. Use `--lang en` for English, or `--stt-model base` after explicitly downloading that model.

## Security and constraints

- No always-on listening. Recording begins only after Enter.
- Audio is temporarily stored in a private temporary directory and removed after transcription. Transcription also uses a temporary WAV file and deletes it.
- Whisper model loading is offline-only at runtime; first download is an explicit setup step.
- No cloud inference, private family memory, authentication, or tool execution is enabled.
- Transcribed text is still hashed in the existing audit log; short utterances can be vulnerable to guessing.
- Five-second fixed recording is a prototype, not silence-detection or wake-word support.
- Whisper CPU inference can take time, especially for the first request.
- Voice responses are not spoken yet. Piper TTS is the next milestone.

## Verification

```bash
uv run --extra voice pytest -q
uv run --extra voice dogy doctor --config config/local-ollama.toml
```

If audio input fails, verify `arecord -l`, then use `--audio-device <device>` for the correct ALSA capture device. Avoid testing with private family information at this stage.

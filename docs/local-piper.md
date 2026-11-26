# Local Piper speech output

This stacked branch builds on `feature/push-to-talk-stt` (PR #2). DOGY still defaults to text-only output. Piper synthesis is opt-in via `--speak`.

## Install and prepare a voice

```bash
uv sync --extra voice
uv run --extra voice pytest -q
mkdir -p voices
# One-time explicit model download; requires internet.
uv run --extra voice python -m piper.download_voices --data-dir voices es_ES-sharvard-medium
```

The voice must provide both `.onnx` and `.onnx.json` files. The above model name is an example; use `uv run --extra voice python -m piper.download_voices` to list available voices if it is unavailable. Keep voice files local and review the model's license before redistribution.

## Run DOGY

```bash
uv run --extra voice dogy voice --lang es --record-seconds 5 --stt-model tiny \
  --config config/local-ollama.toml --speak \
  --tts-model voices/es_ES-sharvard-medium.onnx
```

Press Enter, speak, wait for the transcript and streamed text, then hear the completed reply. Use a matching English Piper voice and `--lang en` for English. To use another ALSA output device, pass `--playback-device <device>`.

## Implementation boundaries

- Piper is launched as a local subprocess, with no shell.
- Audio is written to a temporary WAV file, played using ALSA, and removed.
- The full LLM response is collected for synthesis **after** text streaming finishes; spoken output is not streamed.
- A failed TTS call reports an error and the next voice request can still run.
- Model downloads are explicit setup steps, not performed by DOGY at runtime.
- Do not use this prototype for private family data: authentication and protected storage are not yet implemented.

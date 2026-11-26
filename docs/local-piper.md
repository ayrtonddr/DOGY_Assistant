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

## Mexican Spanish voice and accuracy/latency tests

The official Piper catalogue includes `es_MX-ald-medium` and `es_MX-claude-high`. Neither is confirmed to be a child voice. Test the Mexican accent before deciding whether to pursue a separate child-style model. Voice model licenses may differ.

```bash
uv run --extra voice python -m piper.download_voices --data-dir voices es_MX-ald-medium
uv run --extra voice python -m piper.download_voices --data-dir voices es_MX-claude-high
```

For a better Spanish recognition comparison, download Whisper `base` explicitly:

```bash
uv run --extra voice python -c 'from faster_whisper import WhisperModel; WhisperModel("base", device="cpu", compute_type="int8")'
```

Run the same spoken questions with `tiny` and `base`, changing `--stt-model`, and measure stages using `--timings`:

```bash
uv run --extra voice dogy voice --lang es --record-seconds 5 --stt-model base \
  --config config/local-ollama.toml --speak --timings \
  --tts-model voices/es_MX-ald-medium.onnx
```

To compare the other Mexican voice, change `--tts-model` to `voices/es_MX-claude-high.onnx`. Time values include fixed-duration recording, STT, response generation, and synthesis **plus playback** (not synthesis-only). For a meaningful comparison, keep questions, microphone, and recording duration consistent.

The invocation normalizer corrects a small set of common transcriptions of DOGY's name at the beginning of the utterance; it does not change the original audio or solve arbitrary transcription errors.

import argparse
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .config import load_config, ConfigError
from .router import respond
from .audit import append_event, verify

def main():
    parser = argparse.ArgumentParser(description="DOGY local-only text prototype")
    parser.add_argument("command", choices=["chat", "voice", "verify-audit", "doctor"])
    parser.add_argument("--lang", choices=["en", "es"], default="en")
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--record-seconds", type=int, default=5)
    parser.add_argument("--stt-model", choices=["tiny", "base", "small"], default="tiny")
    parser.add_argument("--audio-device", default="default")
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        ZoneInfo(args.timezone)
    except (ConfigError, FileNotFoundError, ZoneInfoNotFoundError) as exc:
        parser.error(str(exc))
    state = Path(cfg["storage"]["state_dir"])
    audit = state / "audit.jsonl"
    if args.command == "doctor":
        print("DOGY configuration: OK (tools disabled, no family auth yet; LLM: " + cfg["llm"]["backend"] + ")")
        return
    if args.command == "verify-audit":
        ok, _ = verify(audit)
        print("Audit chain: OK" if ok else "Audit chain: INVALID")
        if not ok:
            raise SystemExit(1)
        return
    llm = None
    if cfg["llm"]["backend"] == "ollama":
        from .llm.ollama import OllamaClient
        settings = cfg["llm"]
        llm = OllamaClient(
            model=settings.get("model", "qwen2.5:3b"),
            endpoint=settings.get("endpoint", "http://127.0.0.1:11434"),
            timeout=float(settings.get("timeout", 90)),
            max_tokens=int(settings.get("max_tokens", 160)),
        )
    if args.command == "voice":
        from .voice.record import record_utterance, RecordingError
        from .voice.stt import WhisperTranscriber, TranscriptionError
        try:
            transcriber = WhisperTranscriber(args.stt_model, args.lang)
        except TranscriptionError as exc:
            parser.error(str(exc))
        print("DOGY push-to-talk. Press Enter to record; type exit to quit.")
        while True:
            try:
                command = input("Press Enter to speak> ").strip().casefold()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if command in {"exit", "quit", "salir"}:
                break
            if command:
                print("Press Enter without text to record.")
                continue
            audio = b""
            try:
                audio = record_utterance(args.record_seconds, args.audio_device)
                message = transcriber.transcribe(audio)
            except (RecordingError, TranscriptionError, ValueError) as exc:
                print("DOGY> Voice input failed:", exc)
                continue
            finally:
                audio = b""
            if not message:
                print("DOGY> No speech detected.")
                continue
            print("You>", message)
            reply = respond(message, args.lang, args.timezone)
            if reply.route == "unsupported" and llm is not None:
                from .llm.ollama import OllamaError
                print("DOGY> ", end="", flush=True)
                try:
                    for chunk in llm.stream(message, args.lang):
                        print(chunk, end="", flush=True)
                    print()
                    route = "llm"
                except OllamaError:
                    print()
                    print("DOGY> Local model unavailable.")
                    route = "llm_error"
            else:
                print("DOGY>", reply.text)
                route = reply.route
            append_event(audit, "conversation_route", {"route": route, "language": args.lang,
                        "input_length": len(message), "input_sha256": hashlib.sha256(message.encode()).hexdigest()})
        return

    print("DOGY local text PoC. Type 'exit' to quit. No user authentication or private storage yet.")
    while True:
        try:
            message = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if message.casefold() in {"exit", "quit", "salir"}:
            break
        if not message:
            continue
        # Rule-only classification first: no model call for deterministic commands.
        reply = respond(message, args.lang, args.timezone)
        if reply.route == "unsupported" and llm is not None:
            from .llm.ollama import OllamaError
            print("DOGY> ", end="", flush=True)
            try:
                for chunk in llm.stream(message, args.lang):
                    print(chunk, end="", flush=True)
                print()
                route = "llm"
            except OllamaError:
                print("\n" + ("El modelo local no está disponible." if args.lang == "es" else "The local model is unavailable."))
                route = "llm_error"
        else:
            print("DOGY>", reply.text)
            route = reply.route
        # No raw utterance or reply is persisted; hashes still allow dictionary guessing for short prompts.
        append_event(audit, "conversation_route", {"route": route, "language": args.lang,
                    "input_length": len(message), "input_sha256": hashlib.sha256(message.encode()).hexdigest()})

if __name__ == "__main__":
    main()

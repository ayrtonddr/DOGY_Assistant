import argparse
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from .config import load_config, ConfigError
from .router import respond
from .audit import append_event, verify

def main():
    parser = argparse.ArgumentParser(description="DOGY local-only text prototype")
    parser.add_argument("command", choices=["chat", "verify-audit", "doctor"])
    parser.add_argument("--lang", choices=["en", "es"], default="en")
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    try:
        cfg = load_config(args.config)
        ZoneInfo(args.timezone)
    except (ConfigError, FileNotFoundError, ZoneInfoNotFoundError) as exc:
        parser.error(str(exc))
    state = Path(cfg["storage"]["state_dir"])
    audit = state / "audit.jsonl"
    if args.command == "doctor":
        print("DOGY configuration: OK (offline, tools disabled, no family auth yet)")
        return
    if args.command == "verify-audit":
        ok, _ = verify(audit)
        print("Audit chain: OK" if ok else "Audit chain: INVALID")
        if not ok:
            raise SystemExit(1)
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
        reply = respond(message, args.lang, args.timezone)
        # No raw utterance or reply is persisted; hashes still allow dictionary guessing for short prompts.
        append_event(audit, "conversation_route", {"route": reply.route, "language": args.lang,
                    "input_length": len(message), "input_sha256": hashlib.sha256(message.encode()).hexdigest()})
        print("DOGY>", reply.text)

if __name__ == "__main__":
    main()

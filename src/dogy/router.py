from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
import re

@dataclass(frozen=True)
class Reply:
    text: str
    route: str = "rules"

def respond(utterance: str, language: str = "en", timezone: str = "UTC") -> Reply:
    q = utterance.strip().casefold()
    spanish = language == "es"
    if re.fullmatch(r"(hola|hello|hi|buenos días|buenas tardes|hey)", q):
        return Reply("¡Hola! Soy DOGY." if spanish else "Hello! I'm DOGY.")
    if q in {"what time is it", "what time is it?", "qué hora es", "¿qué hora es?", "que hora es"}:
        now = datetime.now(ZoneInfo(timezone)).strftime("%H:%M")
        return Reply(f"Son las {now}." if spanish else f"It's {now}.")
    if q in {"help", "ayuda"}:
        return Reply("Puedes decir hola o preguntar la hora. Las funciones privadas aún están desactivadas." if spanish else "Say hello or ask for the time. Private features are not enabled yet.")
    return Reply("Todavía no puedo responder eso sin el modelo local. No enviaré datos a la nube." if spanish else "I can't answer that yet without a local model. I won't send data to the cloud.", "unsupported")

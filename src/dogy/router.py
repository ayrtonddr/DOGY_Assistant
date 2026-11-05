from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import TYPE_CHECKING
import re

if TYPE_CHECKING:
    from .llm.base import LLMProvider

@dataclass(frozen=True)
class Reply:
    text: str
    route: str = "rules"

def respond(utterance: str, language: str = "en", timezone: str = "UTC",
            llm: "LLMProvider | None" = None) -> Reply:
    q = utterance.strip().casefold()
    spanish = language == "es"
    if re.fullmatch(r"(hola|hello|hi|buenos días|buenas tardes|hey)", q):
        return Reply("¡Hola! Soy DOGY." if spanish else "Hello! I'm DOGY.")
    if q in {"what time is it", "what time is it?", "qué hora es", "¿qué hora es?", "que hora es"}:
        now = datetime.now(ZoneInfo(timezone)).strftime("%H:%M")
        return Reply(f"Son las {now}." if spanish else f"It's {now}.")
    if q in {"help", "ayuda"}:
        return Reply("Puedes decir hola o preguntar la hora. Las funciones privadas aún están desactivadas." if spanish else "Say hello or ask for the time. Private features are not enabled yet.")
    if llm is not None:
        from .llm.ollama import OllamaError
        try:
            answer = llm.generate(utterance, language)
            if answer:
                return Reply(answer, "llm")
        except OllamaError:
            return Reply("El modelo local no está disponible. Intenta de nuevo." if spanish else "The local model is unavailable. Please try again.", "llm_error")
    return Reply("Todavía no puedo responder eso sin el modelo local. No enviaré datos a la nube." if spanish else "I can't answer that yet without a local model. I won't send data to the cloud.", "unsupported")

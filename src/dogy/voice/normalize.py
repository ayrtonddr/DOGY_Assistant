"""Conservative correction of the assistant's name in Spanish transcripts."""
import re

# Only normalize the invocation at the beginning, not arbitrary words in questions.
_NAME = re.compile(
    r"^(?P<prefix>[¿¡\\s]*)(?P<name>doggy|doggie|doge|dógui|dogui|dokey|doki|dogy)"
    r"(?=\\b|[,.:;!?])", re.IGNORECASE
)


def normalize_invocation(text: str) -> str:
    return _NAME.sub(lambda m: m.group("prefix") + "DOGY", text, count=1)

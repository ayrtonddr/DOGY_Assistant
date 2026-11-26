import pytest
from dogy.voice.normalize import normalize_invocation


@pytest.mark.parametrize("utterance", [
    "Doge, cuéntame un chiste.",
    "Dokey, cuéntame un chiste.",
    "¿Dógui, cuéntame un chiste?",
    "Doggy, qué hora es",
    "Dogy, qué hora es",
])
def test_normalizes_assistant_invocation(utterance):
    assert "DOGY" in normalize_invocation(utterance)


def test_does_not_change_unrelated_words():
    assert normalize_invocation("Me gusta el doge meme") == "Me gusta el doge meme"
    assert normalize_invocation("dogecoin") == "dogecoin"

from __future__ import annotations
from nlp.intents.classifier import classify
from nlp.intents.schema import IntentMatch


def parse(text: str) -> IntentMatch:
    return classify(text)

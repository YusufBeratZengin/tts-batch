"""Lightweight script markup and heuristic multilingual sentence splitting."""

import math
import re
from dataclasses import dataclass

_TITLES = {"mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "sn", "doç", "av"}
_ABBREVIATIONS = {"e.g", "i.e", "vs", "etc", "approx", "no", "fig", "örn", "vb", "bkz", "yy"}
_MONTHS = {
    "ocak",
    "şubat",
    "mart",
    "nisan",
    "mayıs",
    "haziran",
    "temmuz",
    "ağustos",
    "eylül",
    "ekim",
    "kasım",
    "aralık",
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}
_CLOSERS = "\"'”’»)]}"


def split_sentences(text: str) -> list[str]:
    """Split common Latin/CJK punctuation; preserve decimals, titles and initials.

    This is a deterministic heuristic, not a language model. Ambiguous abbreviations
    and punctuation-free languages may require explicit markup boundaries.
    """
    text = re.sub(r"\s+", " ", text).strip()
    result = []
    start = i = 0
    while i < len(text):
        char = text[i]
        if char not in ".!?。！？…":
            i += 1
            continue
        if char == ".":
            before = text[:i]
            after = text[i + 1 :]
            if before[-1:].isdigit() and after[:1].isdigit():
                i += 1
                continue
            token = re.search(r"([\w.]+)$", before, re.UNICODE)
            word = token.group(1) if token else ""
            next_word = after.lstrip()
            next_token = re.match(r"[\w]+", next_word, re.UNICODE)
            next_first_word = next_token.group(0) if next_token else ""
            if next_word and (
                word.casefold() in _TITLES | _ABBREVIATIONS
                or (len(word) == 1 and word.isalpha() and word.isupper())
                or re.fullmatch(r"(?:[A-Za-z]\.)+[A-Za-z]", word)
                or (
                    word.isdigit()
                    and (next_word[0].islower() or next_first_word.casefold() in _MONTHS)
                )
            ):
                i += 1
                continue
            # Inside a domain, abbreviation or dotted initialism.
            if after and not after[0].isspace() and after[0].isalnum():
                i += 1
                continue
        end = i + 1
        while end < len(text) and text[end] in ".!?。！？…" + _CLOSERS:
            end += 1
        # Latin punctuation needs a space/end; CJK punctuation does not.
        if end < len(text) and not text[end].isspace() and char not in "。！？":
            i = end
            continue
        sentence = text[start:end].strip()
        if sentence:
            result.append(sentence)
        start = end
        i = end
    if text[start:].strip():
        result.append(text[start:].strip())
    return result


@dataclass(frozen=True)
class Speech:
    text: str
    voice: str
    speed: float


@dataclass(frozen=True)
class Pause:
    seconds: float


def positive_speed(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("Speed must be finite and greater than zero")
    return value


def parse_script(text: str, voice: str = "", speed: float = 1.0) -> list[Speech | Pause]:
    """Directives flush speech; voice/speed persist and pauses add silence."""
    positive_speed(speed)
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))
    events: list[Speech | Pause] = []

    def emit(chunk: str) -> None:
        # Emphasis is intentionally ignored by the portable engine interface.
        chunk = re.sub(r"\*([^*]+)\*", r"\1", chunk)
        events.extend(Speech(sentence, voice, speed) for sentence in split_sentences(chunk))

    position = 0
    for match in re.finditer(r"\[([^\[\]\n]*)\]", text):
        emit(text[position : match.start()])
        directive = match.group(1).strip()
        name, _, value = directive.partition(" ")
        value = value.strip()
        if name == "pause" and re.fullmatch(r"\d+(?:\.\d+)?ms", value):
            seconds = float(value[:-2]) / 1000
            if not math.isfinite(seconds):
                raise ValueError("Pause must be finite")
            events.append(Pause(seconds))
        elif name == "speed":
            try:
                speed = positive_speed(float(value))
            except ValueError as exc:
                raise ValueError(f"Invalid speed directive: [{directive}]") from exc
        elif name == "voice" and value:
            voice = value
        else:
            raise ValueError(f"Invalid or unknown directive: [{directive}]")
        position = match.end()
    emit(text[position:])
    if any("[" in event.text or "]" in event.text for event in events if isinstance(event, Speech)):
        raise ValueError("Unbalanced markup brackets")
    return events

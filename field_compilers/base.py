"""Base classes and shared utilities for field compilers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CompilerBase(ABC):
    """Abstract base class for all field compilers.

    Each compiler produces the text content for exactly one labeled output field
    (Subject, Clothing, Action, Objects, Environment, Lighting, Camera, Style).
    """

    @abstractmethod
    def process(self, **context) -> str:
        """Produce the text content for this compiler's field.

        Args:
            **context: Compiler-specific keyword arguments containing the
                       fragments, scene data, and references needed.

        Returns:
            The rendered text for this field, or an empty string if no data.
        """
        ...


# ── Shared formatting helpers ──────────────────────────────────────────


def natural_join(items: list[str]) -> str:
    """Join a list of strings with commas and 'and' for the last item."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return ", ".join(items[:-1]) + f", and {items[-1]}"


def join_with_over(items: list[str]) -> str:
    """Join clothing items with 'over' for layering."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} over {items[1]}"
    return f"{items[0]} over " + natural_join(items[1:])


def cap_sentence(text: str) -> str:
    """Capitalize the first letter and ensure the text ends with a period."""
    if not text:
        return ""
    text = text.strip()
    if text:
        text = text[0].upper() + text[1:]
    if text and not text.endswith("."):
        text += "."
    return text


def a_or_an(word: str) -> str:
    """Return the correct indefinite article ('a' or 'an') for a word."""
    if not word:
        return "a"
    first = word[0].lower()
    return "an" if first in "aeiou" else "a"


def strip_article(phrase: str) -> str:
    """Remove leading article ('a ', 'an ', 'the ') from a phrase if present."""
    for art in ("a ", "an ", "the "):
        if phrase.lower().startswith(art):
            return phrase[len(art):].strip()
    return phrase


PRONOUN_VERB = {
    "She": ("She", "is", "wears"),
    "He": ("He", "is", "wears"),
    "They": ("They", "are", "wear"),
}


def pronoun_verb(pronoun: str) -> tuple:
    """Return (subject, be-verb, wear-verb) for a given pronoun."""
    return PRONOUN_VERB.get(pronoun, ("They", "are", "wear"))


SUBJECT_PLURALS = {
    "woman": "women",
    "man": "men",
    "person": "people",
    "child": "children",
    "girl": "girls",
    "boy": "boys",
    "orc": "orcs",
    "elf": "elves",
    "creature": "creatures",
    "human": "humans",
    "adult": "adults",
}


def pluralize_subject(subj_type: str) -> str:
    """Return the plural form of a subject type string."""
    return SUBJECT_PLURALS.get(subj_type, subj_type + "s")

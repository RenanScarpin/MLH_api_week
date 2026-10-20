from __future__ import annotations

import re
import unicodedata

ANSWER_NORMALIZATION_VERSION = 1

_SEPARATOR_RE = re.compile(r"[-_/(),:;]+")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_answer(value: str) -> str:
    """Mirror frontend/src/quiz/normalizeAnswer.ts normalization version 1."""
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.lower()
    value = re.sub(r"[.’'`]", "", value)
    value = _SEPARATOR_RE.sub(" ", value)
    value = "".join(char if (char.isalnum() or char.isspace()) else " " for char in value)
    return _WHITESPACE_RE.sub(" ", value).strip()

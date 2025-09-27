from __future__ import annotations

import re
from functools import lru_cache
from typing import Iterable, List

try:
    from razdel import tokenize
    RAZDEL_AVAILABLE = True
except ImportError:
    RAZDEL_AVAILABLE = False
    def tokenize(text):
        # Simple fallback tokenization
        import re
        return [type('Token', (), {'text': word})() for word in re.findall(r'\w+', text)]


_WORD_RE = re.compile(r"[\w\-]+", re.UNICODE)


@lru_cache(maxsize=1)
def _morph():
    try:
        from pymorphy3 import MorphAnalyzer
        return MorphAnalyzer()
    except ImportError:  # pragma: no cover - optional dependency guard
        return None


def normalize_text(text: str) -> str:
    """Lowercase, lemmatize, and strip noisy characters."""

    if not text:
        return ""
    tokens: List[str] = []
    morph = _morph()
    
    # If pymorphy3 is not available, use simple tokenization
    if morph is None:
        return text.lower()
    
    for token in tokenize(text):
        raw = token.text.lower()
        if not _WORD_RE.fullmatch(raw):
            continue
        parsed = morph.parse(raw)
        if not parsed:
            tokens.append(raw)
            continue
        lemma = parsed[0].normal_form
        tokens.append(lemma)
    return " ".join(tokens)


def tokenize_lemmas(text: str) -> List[str]:
    normalized = normalize_text(text)
    return [token for token in normalized.split() if token]


def contains_any(text: str, candidates: Iterable[str]) -> bool:
    haystack = normalize_text(text)
    return any(candidate in haystack for candidate in candidates)


__all__ = ["contains_any", "normalize_text", "tokenize_lemmas"]

"""NLU schema, validation and the offline rule-based parser (no API key needed)."""
from __future__ import annotations

import re
from typing import Dict, List, Optional

from .locations import LocationIndex, norm

LANGUAGES = {
    "en": "English", "hi": "Hindi", "kn": "Kannada", "te": "Telugu",
    "ta": "Tamil", "mr": "Marathi", "bn": "Bengali", "gu": "Gujarati",
}
INTENTS = {"greet", "help", "list_states", "lookup", "compare", "ranking", "categories", "unknown"}
METRIC_NAMES = {"rainfall", "extraction", "recharge", "availability", "overview"}
CATEGORIES = {"safe", "semi_critical", "critical", "over_exploited"}


def empty_nlu() -> dict:
    return {"language": "en", "intent": "unknown", "metric": "overview", "locations": [],
            "level": "district", "order": "desc", "limit": 5, "category": None}


def sanitize(raw: dict) -> dict:
    """Never trust model output: clamp everything to the allowed values."""
    out = empty_nlu()
    if not isinstance(raw, dict):
        return out
    lang = str(raw.get("language", "en")).lower()[:2]
    out["language"] = lang if lang in LANGUAGES else "en"
    intent = str(raw.get("intent", "unknown")).lower()
    out["intent"] = intent if intent in INTENTS else "unknown"
    metric = str(raw.get("metric") or "overview").lower()
    out["metric"] = metric if metric in METRIC_NAMES else "overview"
    locs = raw.get("locations") or []
    if isinstance(locs, str):
        locs = [locs]
    out["locations"] = [str(x).strip()[:60] for x in locs if str(x).strip()][:4]
    out["level"] = "state" if str(raw.get("level", "")).lower() == "state" else "district"
    out["order"] = "asc" if str(raw.get("order", "")).lower() == "asc" else "desc"
    try:
        out["limit"] = max(1, min(10, int(raw.get("limit") or 5)))
    except (TypeError, ValueError):
        out["limit"] = 5
    cat = str(raw.get("category") or "").lower().replace("-", "_").replace(" ", "_")
    out["category"] = cat if cat in CATEGORIES else None
    return out


# ---------------------------------------------------------------- language
_SCRIPTS = [  # (regex, language)
    (r"[\u0980-\u09FF]", "bn"), (r"[\u0A80-\u0AFF]", "gu"), (r"[\u0B80-\u0BFF]", "ta"),
    (r"[\u0C00-\u0C7F]", "te"), (r"[\u0C80-\u0CFF]", "kn"),
]
_MARATHI_HINTS = ("आहे", "पाऊस", "किती", "आणि", "मध्ये", "माहिती")


def detect_language(text: str) -> str:
    for pattern, lang in _SCRIPTS:
        if re.search(pattern, text):
            return lang
    if re.search(r"[\u0900-\u097F]", text):
        return "mr" if any(h in text for h in _MARATHI_HINTS) else "hi"
    return "en"


# ---------------------------------------------------------------- keywords
def _kw(*words: str) -> List[str]:
    return list(words)

KEYWORDS: Dict[str, List[str]] = {
    "rainfall": _kw("rainfall", "rain", "वर्षा", "बारिश", "पाऊस", "ಮಳೆ", "వర్షం", "వర్షపాతం", "மழை", "বৃষ্টি", "વરસાદ"),
    "extraction": _kw("extraction", "extracted", "stage", "निष्कर्षण", "निकासी", "उपसा", "ಹೊರತೆಗೆ", "వెలికితీ", "பிரித்தெடு", "উত্তোলন", "નિષ્કર્ષણ"),
    "recharge": _kw("recharge", "पुनर्भरण", "रिचार्ज", "ಮರುಪೂರಣ", "రీఛార్జ్", "ரீசார்ஜ்", "রিচার্জ", "રિચાર્જ"),
    "availability": _kw("availability", "available", "उपलब्ध", "ಲಭ್ಯ", "అందుబాటు", "கிடைக்க", "উপলব্ধ", "ઉપલબ્ધ"),
    "compare": _kw("compare", "comparison", "versus", "difference", "तुलना", "ಹೋಲಿಕೆ", "పోలిక", "ஒப்பிட", "তুলনা", "સરખામણી"),
    "ranking": _kw("top", "highest", "lowest", "most", "least", "best", "worst", "maximum", "minimum", "driest", "wettest", "rank",
                   "सबसे", "सर्वाधिक", "ಹೆಚ್ಚು", "అత్యధిక", "அதிக", "সবচেয়ে", "સૌથી"),
    "asc": _kw("lowest", "least", "minimum", "driest", "fewest", "smallest", "bottom", "सबसे कम", "ಕಡಿಮೆ", "తక్కువ", "குறைந்த", "সবচেয়ে কম", "સૌથી ઓછા"),
    "greet": _kw("hello", "hi", "hey", "namaste", "namaskar", "good morning", "good evening", "नमस्ते", "नमस्कार", "ನಮಸ್ಕಾರ", "నమస్కారం", "வணக்கம்", "নমস্কার", "નમસ્તે"),
    "help": _kw("help", "what can you do", "how to use", "मदद", "सहायता"),
}
CATEGORY_PATTERNS = [
    ("over_exploited", r"over[\s-]?exploit|overexploit"),
    ("semi_critical", r"semi[\s-]?critical"),
    ("critical", r"\bcritical\b"),
    ("safe", r"\bsafe\b"),
]


def _has(text: str, words: List[str]) -> bool:
    for w in words:
        if w.isascii():
            if re.search(r"\b" + re.escape(w) + r"\b", text):
                return True
        elif w in text:
            return True
    return False


def rule_parse(message: str, index: LocationIndex, hint_state: Optional[str] = None) -> dict:
    """Offline fallback. English works fully; Indic scripts work for the core
    keywords but place names must be written in English letters."""
    out = empty_nlu()
    text = message.lower()
    out["language"] = detect_language(message)
    locs = index.find_all(message, hint_state)
    out["locations"] = [l.label for l in locs]
    states_only = [l for l in locs if l.kind == "state"]

    # metric
    for metric in ("rainfall", "extraction", "recharge", "availability"):
        if _has(text, KEYWORDS[metric]):
            out["metric"] = metric
            break
    if re.search(r"\b(driest|wettest)\b", text):
        out["metric"] = "rainfall"

    # category filter
    for cat, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, text):
            out["category"] = cat
            break

    m = re.search(r"\b(?:top|first|bottom|lowest|highest)\s+(\d{1,2})\b", text) or re.search(r"\b(\d{1,2})\s+(?:districts|states)\b", text)
    if m:
        out["limit"] = max(1, min(10, int(m.group(1))))
    if _has(text, KEYWORDS["asc"]):
        out["order"] = "asc"
    if re.search(r"\bstates\b", text) and not re.search(r"\bdistricts?\b", text):
        out["level"] = "state"

    words = norm(message).split()
    short = len(words) <= 4
    wants_list = re.search(r"\b(list|show|all|which|available|what)\b", text) and re.search(r"\bstates\b", text)

    if _has(text, KEYWORDS["greet"]) and short and not locs and out["metric"] == "overview":
        out["intent"] = "greet"
    elif _has(text, KEYWORDS["help"]) and not locs:
        out["intent"] = "help"
    elif wants_list and not locs and not out["category"] and not _has(text, KEYWORDS["ranking"]):
        out["intent"] = "list_states"
    elif _has(text, KEYWORDS["compare"]) or re.search(r"\b(vs|v/s|versus)\b", text) or (len(locs) >= 2 and re.search(r"\b(and|with|or)\b", text) and re.search(r"\b(compare|between|difference)\b", text)):
        out["intent"] = "compare" if len(locs) >= 2 else "unknown"
        if out["intent"] == "unknown" and locs:
            out["intent"] = "lookup"
    elif out["category"] or _has(text, KEYWORDS["ranking"]):
        out["intent"] = "ranking" if (out["category"] or len(locs) <= 1) else "lookup"
        if out["category"] and re.search(r"\bhow many\b|\bcount\b|\bnumber of\b", text):
            out["intent"] = "categories"
        if out["metric"] == "overview":
            out["metric"] = "extraction"
        if states_only and out["level"] == "state":
            out["level"] = "district"
    elif locs:
        out["intent"] = "lookup"
    elif out["metric"] != "overview":
        out["intent"] = "lookup"
        # "rainfall in Atlantis": keep the unknown place so we can say we don't know it
        m = re.search(r"\b(?:in|of|for|at|about)\s+([a-z][a-z .'-]{2,40})$", text.strip(" ?!."))
        leftover = [w for w in (m.group(1).split() if m else [])
                    if w not in {"the", "state", "district", "india", "all", "whole", "country", "overall"}]
        out["locations"] = [" ".join(leftover)] if leftover else ["India"]
    return out

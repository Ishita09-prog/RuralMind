"""
Language utilities for RuralMind.

One place to:
  - detect the language of a piece of text          -> detect_language()
  - turn a language code into a human name           -> language_name()
  - turn a language code into a gTTS voice code       -> gtts_lang()

How detection works:
  - Text in a NON-Latin script (Devanagari, Tamil, Arabic, Chinese...) is
    detected with langdetect, which is reliable there.
  - Text in Latin/English letters could be English OR a romanized Indian
    language (Hinglish like "barish kaise hoti hai", Tanglish like
    "force na enna"). langdetect is UNRELIABLE here (it often guesses
    Swahili/Tagalog/Indonesian), so we use a small keyword heuristic instead
    and return special codes 'hi-rom' / 'ta-rom'.
"""

import re
from langdetect import detect, DetectorFactory

# Make langdetect deterministic (short text can otherwise flip between runs)
DetectorFactory.seed = 0


# Common words that signal romanized Hindi (Hinglish) vs romanized Tamil
# (Tanglish). Lowercase, no punctuation.
# Distinctive words only. Short words that collide with European languages
# (se, na, da, nu, etc.) are intentionally left out to avoid false matches.
ROMANIZED_HI = {
    "kya", "hai", "hain", "kaise", "kaisi", "kyun", "kyon", "kyu", "hoti",
    "hota", "hote", "kaun", "nahi", "nahin", "haan", "acha", "accha", "batao",
    "matlab", "samajh", "samjhao", "kahan", "mera", "meri", "tera", "tum",
    "tumhara", "aap", "karo", "karta", "raha", "rahi", "rahe", "kuch", "yeh",
    "woh", "bohot", "bahut", "kyunki", "lekin", "padta", "padhna", "hota",
}

ROMANIZED_TA = {
    "enna", "epdi", "eppadi", "illa", "irukku", "iruku", "panra", "panna",
    "pannu", "pannanum", "sollu", "solunga", "theriyuma", "theriyum", "evlo",
    "romba", "vandhu", "aagum", "eppo", "enga", "yaaru", "venum", "vendam",
    "seri", "paaru", "podhum", "kashtam", "nalla", "rendu", "moonu",
}


# langdetect / romanized code  ->  human readable name (used to hint the LLM)
LANGUAGE_NAMES = {
    "af": "Afrikaans", "ar": "Arabic", "bg": "Bulgarian", "bn": "Bengali",
    "ca": "Catalan", "cs": "Czech", "cy": "Welsh", "da": "Danish",
    "de": "German", "el": "Greek", "en": "English", "es": "Spanish",
    "et": "Estonian", "fa": "Persian", "fi": "Finnish", "fr": "French",
    "gu": "Gujarati", "he": "Hebrew", "hi": "Hindi", "hr": "Croatian",
    "hu": "Hungarian", "id": "Indonesian", "it": "Italian", "ja": "Japanese",
    "kn": "Kannada", "ko": "Korean", "lt": "Lithuanian", "lv": "Latvian",
    "mk": "Macedonian", "ml": "Malayalam", "mr": "Marathi", "ne": "Nepali",
    "nl": "Dutch", "no": "Norwegian", "pa": "Punjabi", "pl": "Polish",
    "pt": "Portuguese", "ro": "Romanian", "ru": "Russian", "sk": "Slovak",
    "sl": "Slovenian", "so": "Somali", "sq": "Albanian", "sv": "Swedish",
    "sw": "Swahili", "ta": "Tamil", "te": "Telugu", "th": "Thai",
    "tl": "Tagalog", "tr": "Turkish", "uk": "Ukrainian", "ur": "Urdu",
    "vi": "Vietnamese", "zh-cn": "Chinese", "zh-tw": "Chinese",
    # Romanized (Latin-script) Indian languages:
    "hi-rom": "Hindi written in English/roman letters (Hinglish)",
    "ta-rom": "Tamil written in English/roman letters (Tanglish)",
}

# code -> gTTS voice code (only where they differ or need fixing).
_GTTS_OVERRIDES = {
    "zh-cn": "zh-CN",
    "zh-tw": "zh-TW",
    "he": "iw",      # gTTS uses the old Hebrew code
    "hi-rom": "hi",  # speak romanized Hindi with the Hindi voice
    "ta-rom": "ta",  # speak romanized Tamil with the Tamil voice
}

# Cache the languages gTTS actually supports so we never crash on a bad code.
try:
    from gtts.lang import tts_langs
    _SUPPORTED_GTTS = set(tts_langs().keys())
except Exception:
    _SUPPORTED_GTTS = {
        "en", "hi", "ta", "te", "kn", "ml", "mr", "bn", "gu", "pa", "ur",
        "fr", "es", "de", "ar", "zh-CN", "ja", "ko", "ru", "pt", "it",
    }


def _is_latin_script(text: str) -> bool:
    """True if the text is mostly English/roman letters (a-z)."""
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return True
    ascii_letters = [c for c in letters if ord(c) < 128]
    return len(ascii_letters) / len(letters) > 0.8


def _is_plain_ascii(text: str) -> bool:
    """True if every letter is plain a-z (no accents like é, ñ, ü)."""
    return all(ord(c) < 128 for c in text if c.isalpha())


def _detect_romanized(text: str) -> str:
    """Classify Latin-script text as 'hi-rom', 'ta-rom', or '' (not romanized)."""
    words = set(re.findall(r"[a-z]+", text.lower()))
    hi_hits = len(words & ROMANIZED_HI)
    ta_hits = len(words & ROMANIZED_TA)
    if hi_hits == 0 and ta_hits == 0:
        return ""  # no romanized signal -> let langdetect decide
    return "hi-rom" if hi_hits >= ta_hits else "ta-rom"


def _cjk_lang(text: str):
    """Resolve Chinese/Japanese/Korean by script (langdetect is shaky on short
    CJK text). Returns a code or None."""
    if any("가" <= c <= "힣" for c in text):   # Hangul
        return "ko"
    if any("぀" <= c <= "ヿ" for c in text):   # Hiragana/Katakana
        return "ja"
    if any("一" <= c <= "鿿" for c in text):   # Han characters
        return "zh-cn"
    return None


def detect_language(text: str) -> str:
    """Return a language code: ISO code, 'hi-rom'/'ta-rom', or 'en' on failure."""
    if not text or not text.strip():
        return "en"

    # Latin-script text: check for Hinglish/Tanglish first (langdetect can't
    # see those).
    if _is_latin_script(text):
        rom = _detect_romanized(text)
        if rom:
            return rom
        # Plain ASCII with no accent marks is almost always English here
        # (langdetect wrongly guesses Danish/Dutch/German on short English).
        # European languages normally carry accents (é, ñ, ü, ¿) -> let
        # langdetect handle those.
        if _is_plain_ascii(text):
            return "en"
        try:
            return detect(text)
        except Exception:
            return "en"

    # Non-Latin script: resolve CJK by script, otherwise langdetect.
    cjk = _cjk_lang(text)
    if cjk:
        return cjk
    try:
        return detect(text)
    except Exception:
        return "en"


def is_romanized(code: str) -> bool:
    """True for our special romanized codes (hi-rom / ta-rom)."""
    return bool(code) and code.endswith("-rom")


def language_name(code: str) -> str:
    """Human readable name for a code, used to hint the LLM."""
    if not code:
        return "English"
    return LANGUAGE_NAMES.get(code.lower(), code)


def gtts_lang(code: str) -> str:
    """Map a detected code to a gTTS voice code, falling back to English."""
    if not code:
        return "en"
    code = code.lower()
    mapped = _GTTS_OVERRIDES.get(code, code)
    if mapped in _SUPPORTED_GTTS:
        return mapped
    short = mapped.split("-")[0]
    if short in _SUPPORTED_GTTS:
        return short
    return "en"

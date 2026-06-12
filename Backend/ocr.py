"""
OCR helper for the photo / textbook question solver.

Reads text from an uploaded image using Tesseract. Supports English + Hindi +
Tamil out of the box (install the language packs, see requirements notes).
Returns "" gracefully if Tesseract or a language pack is missing.
"""

import io

# Default languages: English + Hindi + Tamil. Add more like "+tel+kan+ben".
DEFAULT_LANGS = "eng+hin+tam"


def image_to_text(image_bytes: bytes, langs: str = DEFAULT_LANGS) -> str:
    try:
        import pytesseract
        from PIL import Image
    except Exception:
        return ""

    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception:
        return ""

    # First try with the requested language packs.
    try:
        return pytesseract.image_to_string(img, lang=langs).strip()
    except Exception:
        pass

    # Fall back to default (English) if a language pack is not installed.
    try:
        return pytesseract.image_to_string(img).strip()
    except Exception:
        return ""

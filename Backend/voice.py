from gtts import gTTS
import uuid
import os

from lang_utils import detect_language, gtts_lang


def delete_old_audio():
    for file in os.listdir("."):
        if file.startswith("audio_") and file.endswith(".mp3"):
            try:
                os.remove(file)
            except OSError:
                pass


def generate_voice(text, language=None):
    """Generate speech for `text` in its own language.

    If `language` (an ISO code like 'hi', 'ta', 'es') is given we use it;
    otherwise we detect it from the text. Falls back to English for any
    language gTTS does not support.
    """
    # Remove previous audio files
    delete_old_audio()

    code = language or detect_language(text)
    voice = gtts_lang(code)

    filename = f"audio_{uuid.uuid4().hex}.mp3"

    try:
        tts = gTTS(text=text, lang=voice)
        tts.save(filename)
    except Exception:
        # Last-resort fallback so the request never crashes on audio.
        tts = gTTS(text=text, lang="en")
        tts.save(filename)

    return f"http://127.0.0.1:8000/audio/{filename}"

from gtts import gTTS
import uuid
import os


def delete_old_audio():
    for file in os.listdir("."):
        if file.startswith("audio_") and file.endswith(".mp3"):
            os.remove(file)


def generate_voice(text, language):

    # Delete previous audio files
    delete_old_audio()

    if language == "hinglish":
        lang = "hi"
    elif language == "tanglish":
        lang = "ta"
    else:
        lang = "en"

    filename = f"audio_{uuid.uuid4().hex}.mp3"

    tts = gTTS(text=text, lang=lang)
    tts.save(filename)

    return f"http://127.0.0.1:8000/audio/{filename}"
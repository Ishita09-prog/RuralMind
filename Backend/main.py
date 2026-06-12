from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rag_engine import retrieve_answer, filter_context
from explainer import (
    explain_text,
    generate_quiz,
    generate_diagram,
    translate_text,
    extract_topic,
    search_diagram_image,
    generate_practice_questions,
)
from voice import generate_voice
from lang_utils import detect_language
from ocr import image_to_text
import json
import re

app = FastAPI()

app.mount("/audio", StaticFiles(directory="."), name="audio")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "RuralMind AI Tutor API is running"}

@app.get("/ask")
def ask_question(question: str, mode: str = "student",
                 grade: str = "", subject: str = "", history: str = "",
                 reply: str = "auto"):

    # Detect the language of the question (any language, real ISO code).
    language = detect_language(question)

    # Parse the recent conversation passed from the frontend (JSON list).
    past = []
    if history:
        try:
            past = json.loads(history)
        except Exception:
            past = []

    raw_answer = retrieve_answer(question)
    raw_answer = filter_context(question, raw_answer)

    raw_answer = re.sub(r'\s+', ' ', raw_answer).strip()

    # 'reply' forces an answer language (e.g. 'te'); 'auto' = match the question.
    answer = explain_text(
        question, raw_answer, language, mode,
        grade=grade, subject=subject, history=past, reply_language=reply,
    )

    # Speak in the forced language if set, else let voice.py detect it.
    if reply and reply not in ("auto", ""):
        audio_file = generate_voice(answer, reply)
    else:
        audio_file = generate_voice(answer)

    return {
        "question": question,
        "answer": answer,
        "language": language,
        "audio": audio_file
    }


@app.post("/ocr")
async def ocr(file: UploadFile = File(...)):
    # Read text from a photo of a textbook question.
    data = await file.read()
    text = image_to_text(data)
    return {"text": text}


@app.get("/worksheet")
def worksheet(question: str):
    # Practice questions for a printable worksheet (frontend adds the notes).
    topic = extract_topic(question)
    questions = generate_practice_questions(question, count=4)
    return {"topic": topic, "questions": questions}

@app.get("/translate")
def translate(text: str, target: str = "en"):
    # Translate any answer into the target language (default English) so the
    # student can also read it in English.
    translated = translate_text(text, target)
    audio_file = generate_voice(translated, target)
    return {"answer": translated, "audio": audio_file}

@app.get("/quiz")
def quiz(question: str, reply: str = "auto"):

    quiz = generate_quiz(question, question, reply_language=reply)

    return {"quiz": quiz}

@app.get("/diagram")
def diagram(question: str):

    # 1) Try to fetch a real labeled diagram image from the web.
    topic = extract_topic(question)
    image_url = search_diagram_image(topic)

    if image_url:
        return {"type": "image", "image": image_url, "topic": topic}

    # 2) Fall back to an auto-generated flowchart so something always shows.
    raw_answer = retrieve_answer(question)
    diagram = generate_diagram(question, raw_answer)
    diagram["type"] = "flow"
    diagram["topic"] = topic
    return diagram

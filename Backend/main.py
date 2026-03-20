from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from rag_engine import retrieve_answer, filter_context
from explainer import explain_text, generate_quiz, generate_diagram
from voice import generate_voice
from langdetect import detect
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

def detect_language(query):
    try:
        lang = detect(query)
        if lang == "hi":
            return "hinglish"
        elif lang == "ta":
            return "tanglish"
        else:
            return "english"
    except:
        return "english"

@app.get("/ask")
def ask_question(question: str, mode: str = "student"):

    language = detect_language(question)

    raw_answer = retrieve_answer(question)
    raw_answer = filter_context(question, raw_answer)

    raw_answer = re.sub(r'\s+', ' ', raw_answer).strip()

    answer = explain_text(question, raw_answer, language, mode)

    audio_file = generate_voice(answer, language)

    return {
        "question": question,
        "answer": answer,
        "audio": audio_file
    }

@app.get("/quiz")
def quiz(question: str):

    quiz = generate_quiz(question, question)

    return {"quiz": quiz}

@app.get("/diagram")
def diagram(question: str):

    raw_answer = retrieve_answer(question)

    diagram = generate_diagram(question, raw_answer)

    return diagram

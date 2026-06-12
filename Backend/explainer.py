import os
import requests
import re

# Load Backend/.env (GOOGLE_API_KEY, GOOGLE_CX) if python-dotenv is available.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from lang_utils import detect_language, language_name, is_romanized

# =========================
# OLLAMA CONFIG
# =========================

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"

# =========================
# GOOGLE IMAGE SEARCH CONFIG
# =========================
# Used to fetch a real labeled diagram for a topic. Reads from environment
# first (recommended), falling back to the project's existing key/CX.
# Set these in Backend/.env (see .env.example). Diagram falls back to Wikimedia
# (no key needed) if these are empty.
# Get your own free key at https://developers.google.com/custom-search/v1/overview
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GOOGLE_CX = os.getenv("GOOGLE_CX", "")


def _ask_ollama(prompt: str) -> str:
    """Send a prompt to the local Ollama model and return the text response."""
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        data = response.json()
        return data.get("response", "").strip()
    except Exception:
        return ""


# =========================
# HYBRID TRANSLATION FALLBACK
# =========================
# The LLM is told to reply in the question's language. If it slips back into
# English for a non-English question, we translate the answer ourselves so the
# student still gets it in their language.

def _looks_english(text: str) -> bool:
    return detect_language(text) == "en"


def _translate(text: str, target_code: str) -> str:
    """Best-effort translate to target language; returns original on failure."""
    if not text or not target_code or target_code == "en":
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target=target_code).translate(text)
    except Exception:
        # Library missing or no internet -> just return what we have.
        return text


def translate_text(text: str, target: str = "en") -> str:
    """Public translator (used by the 'English' button). Returns original on failure."""
    if not text or not text.strip():
        return text
    try:
        from deep_translator import GoogleTranslator
        return GoogleTranslator(source="auto", target=target).translate(text)
    except Exception:
        return text


def _match_language(answer: str, question_code: str) -> str:
    """If the answer drifted to English but the question wasn't, fix it.

    Skipped for English and for romanized questions (Hinglish/Tanglish), whose
    correct answers are written in roman letters and would look English here.
    """
    if not answer:
        return answer
    if question_code == "en" or is_romanized(question_code):
        return answer
    if _looks_english(answer):
        return _translate(answer, question_code)
    return answer


# =========================
# TEXT EXPLANATION
# =========================

# How long / how deep the answer should be, per mode.
DEPTH_RULES = {
    "kid": "Explain like talking to a curious 8-year-old child. Use very "
           "simple words and a warm tone. Keep it to about 4 short sentences.",
    "student": "Explain clearly for a school student. Use simple words. "
               "Maximum 5 sentences.",
    "exam": "Give an exam-focused answer with the key points a student should "
            "write to score marks. About 5 to 6 clear sentences.",
    "detailed": "Explain thoroughly, like a patient tutor teaching the topic "
                "step by step. First give a simple definition, then explain how "
                "and why it works, then give ONE everyday real-life example, and "
                "finish with a one-line summary. Use simple words and short "
                "sentences. Write about 8 to 12 sentences. You may break it into "
                "short paragraphs.",
    "guide": "Do NOT give the final answer directly. Act like a patient teacher "
             "helping the student discover it themselves: ask ONE simple leading "
             "question, give a small hint, and encourage them to try. Keep it to "
             "3 to 4 short sentences.",
}


def _format_history(history) -> str:
    """Turn a list of {role, text} turns into a short conversation block."""
    if not history:
        return ""
    lines = []
    for turn in history[-6:]:  # keep it short
        role = turn.get("role", "")
        msg = (turn.get("text") or "").strip()
        if not msg:
            continue
        who = "Student" if role == "user" else "Tutor"
        lines.append(f"{who}: {msg}")
    if not lines:
        return ""
    return (
        "PREVIOUS CONVERSATION (use this to understand short follow-ups like "
        "\"explain more\", \"why?\", \"give an example\"; reply about the SAME "
        "topic):\n" + "\n".join(lines) + "\n"
    )


def explain_text(question, text, language="auto", mode="student",
                 grade="", subject="", history=None, reply_language="auto"):
    # Decide the target language.
    forced = bool(reply_language) and reply_language not in ("auto", "")
    if forced:
        target_code = reply_language
    else:
        # Auto: language comes ONLY from the current question.
        target_code = detect_language(question)
    lang_label = language_name(target_code)

    depth_rule = DEPTH_RULES.get(mode, DEPTH_RULES["student"])
    history_block = _format_history(history)

    level_line = ""
    if grade or subject:
        bits = []
        if grade:
            bits.append(f"class/grade {grade}")
        if subject:
            bits.append(f"the subject {subject}")
        level_line = ("- The student is in " + " studying ".join(bits) +
                      ". Match that level and syllabus.\n")

    if forced:
        language_rule = (
            "THE MOST IMPORTANT RULE - LANGUAGE:\n"
            f"- Write your ENTIRE answer in {lang_label} ONLY, using the "
            f"{lang_label} script.\n"
            "- Do this NO MATTER what language the question or the previous "
            "conversation is in.\n"
            "- Do not mix in any other language.\n"
        )
    else:
        language_rule = (
            "THE MOST IMPORTANT RULE - LANGUAGE:\n"
            "- Choose the answer language ONLY from the CURRENT QUESTION below.\n"
            "- IGNORE the language used earlier in the conversation - earlier "
            "messages are only for understanding the topic, NOT the language.\n"
            "- Write your ENTIRE answer in the SAME language and SAME script as "
            "the current question.\n"
            f"- Our detector guessed: {lang_label}. Trust the actual question "
            "text over this guess.\n"
            "- If the question is in roman/English letters (Hinglish "
            "\"barish kaise hoti hai\" or Tanglish \"force na enna\"), answer in "
            "that same roman style.\n"
            "- If the question is in plain English, answer in plain English.\n"
            "- Never translate the question or add meanings in brackets.\n"
        )

    prompt = f"""
You are RuralMind, a friendly tutor for students in rural areas.

{language_rule}
{history_block}
HOW TO ANSWER:
- {depth_rule}
{level_line}- Use simple, clear words a rural student can understand.
- Use the context only for facts, NOT for choosing the language.

CURRENT QUESTION:
{question}

CONTEXT (facts only):
{text}
"""

    answer = _ask_ollama(prompt)
    if not answer:
        return "Sorry, explanation could not be generated."

    # Safety net: make sure the answer is actually in the target language.
    if forced:
        # A specific language was requested. llama3 is unreliable for many
        # languages, so ALWAYS translate to guarantee the right language.
        # (Needs internet; if translation fails it returns the model's text.)
        if target_code != "en":
            answer = _translate(answer, target_code)
    else:
        answer = _match_language(answer, target_code)
    return answer.strip()


# =========================
# PRACTICE QUESTIONS (for worksheet export)
# =========================

def generate_practice_questions(topic, count=4):
    """Return a list of short practice questions in the topic's language."""
    question_code = detect_language(topic)
    lang_label = language_name(question_code)

    prompt = f"""
Create {count} short practice questions for a student about the topic below.

LANGUAGE RULE:
- Write the questions in the SAME language and script as the topic
  (detector guessed {lang_label}, but trust the actual topic text).

Topic:
{topic}

Rules:
- One question per line.
- Number them 1) 2) 3) ...
- Mix easy and slightly harder questions.
- Do NOT write the answers.
"""

    text = _ask_ollama(prompt)
    questions = []
    for line in text.split("\n"):
        line = line.strip()
        line = re.sub(r"^\d+[\).\-:]\s*", "", line)  # strip leading "1) "
        if len(line) > 4:
            questions.append(line)
    return questions[:count] if questions else [
        "Write what you understood about this topic in your own words.",
    ]


# =========================
# QUIZ GENERATION
# =========================

def generate_quiz(question, context, reply_language="auto"):
    # Always generate the quiz in ENGLISH so the A) B) C) format parses
    # reliably, then translate into the target language. This avoids llama3
    # producing random languages when asked to write directly in e.g. Telugu.
    prompt = f"""
Generate ONE multiple-choice question in ENGLISH about the topic below.

Topic:
{question}

Format EXACTLY like this:

Question: ...
A) ...
B) ...
C) ...
Correct Answer: A/B/C
"""

    text = _ask_ollama(prompt)
    if not text:
        return {"question": "Quiz generation failed", "options": [], "answer": ""}

    question_match = re.search(r"Question:\s*(.*)", text)
    options = re.findall(r"[A-C]\)\s*(.*)", text)
    answer_match = re.search(r"Correct Answer:\s*([A-C])", text)

    question_text = question_match.group(1).strip() if question_match else ""
    options = [o.strip() for o in options]
    answer_letter = answer_match.group(1) if answer_match else ""
    correct_index = {"A": 0, "B": 1, "C": 2}.get(answer_letter, 0)

    # Decide target language: forced choice, else the topic's own language.
    forced = bool(reply_language) and reply_language not in ("auto", "")
    target_code = reply_language if forced else detect_language(question)

    # Translate question + options into the target language (if not English).
    if target_code and target_code != "en":
        question_text = _translate(question_text, target_code)
        options = [_translate(o, target_code) for o in options]

    answer_text = options[correct_index] if correct_index < len(options) else ""

    return {
        "question": question_text,
        "options": options,
        "answer": answer_text,
    }


# =========================
# DIAGRAM: REAL IMAGE FROM WEB
# =========================

def extract_topic(text: str) -> str:
    """Reduce a long answer/question to a short English topic for searching."""
    prompt = (
        "What is the main science topic in the text below? "
        "Reply with ONLY 1 to 3 English words, nothing else.\n\n"
        f"Text:\n{text}"
    )
    out = _ask_ollama(prompt)
    out = out.split("\n")[0].strip(' ."\'')
    # Reject empty or rambling answers; fall back to first words of the text.
    if not out or len(out) > 40:
        words = re.findall(r"[A-Za-z]+", text)
        out = " ".join(words[:3])
    return out or "science"


def _wikimedia_image(topic: str):
    """Free, no-key labeled diagrams from Wikimedia Commons. Returns URL or None."""
    try:
        resp = requests.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"{topic} diagram",
                "gsrnamespace": 6,          # File: namespace
                "gsrlimit": 12,
                "prop": "imageinfo",
                "iiprop": "url|mime",
                "format": "json",
            },
            headers={"User-Agent": "RuralMind/1.0 (educational tutor)"},
            timeout=15,
        )
        pages = resp.json().get("query", {}).get("pages", {})
        candidates = []
        for p in pages.values():
            info = (p.get("imageinfo") or [{}])[0]
            url = info.get("url", "")
            mime = info.get("mime", "")
            if url and mime.startswith("image/"):
                candidates.append(url)
        # Prefer raster/SVG diagrams; browsers render all of these in <img>.
        for url in candidates:
            if url.lower().endswith((".png", ".jpg", ".jpeg", ".svg", ".gif")):
                return url
        if candidates:
            return candidates[0]
    except Exception:
        pass
    return None


def _google_image(topic: str):
    """Fallback image search via Google Custom Search (needs key + quota)."""
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        return None
    try:
        resp = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "key": GOOGLE_API_KEY,
                "cx": GOOGLE_CX,
                "q": f"{topic} labelled diagram",
                "searchType": "image",
                "num": 5,
                "safe": "active",
            },
            timeout=15,
        )
        items = resp.json().get("items", [])
        for it in items:
            link = it.get("link", "")
            if link.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
                return link
        if items:
            return items[0].get("link")
    except Exception:
        pass
    return None


def search_diagram_image(topic: str):
    """Return the URL of a labeled diagram image for `topic`, or None.

    Tries Wikimedia Commons first (free, no key), then Google as a fallback.
    """
    return _wikimedia_image(topic) or _google_image(topic)


# =========================
# DIAGRAM FLOWCHART (FALLBACK)
# =========================

def generate_diagram(question, context):
    question_code = detect_language(question)
    lang_label = language_name(question_code)

    prompt = f"""
You are RuralMind, an AI science tutor.

LANGUAGE RULE (MOST IMPORTANT):
- Detect the language and script of the QUESTION (our detector guessed
  {lang_label}, but trust the actual question text).
- Write every step in that SAME language and SAME script.
- If the question is in roman/English letters, keep the steps in that roman
  style. Never switch languages mid-answer. Never add English meanings.
- Keep the word "Step1:", "Step2:", "Step3:" labels in English so they parse.

Make the explanation very simple and student-friendly.

QUESTION:
{question}

CONTEXT (for facts only, NOT for language):
{context}

Format:
Step1: ...
Step2: ...
Step3: ...
"""

    text = _ask_ollama(prompt)

    steps = []
    for line in text.split("\n"):
        if "Step" in line:
            steps.append(line.split(":", 1)[-1].strip().replace("*", ""))

    if len(steps) < 3:
        steps = ["Start", "Process", "Result"]

    return {
        "nodes": [
            {"id": str(i + 1), "label": steps[i]}
            for i in range(len(steps))
        ],
        "links": [
            {"source": str(i + 1), "target": str(i + 2)}
            for i in range(len(steps) - 1)
        ],
    }

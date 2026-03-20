import requests
import json
import re
from googleapiclient.discovery import build

# =========================
# GOOGLE IMAGE SEARCH CONFIG
# =========================

API_KEY = "AIzaSyA3VNcNsz1moYKT8P-5pVo5jXJJyOAIxL8" #GOOGLE API KEYY
CX = "868a2edff9b244bae" #SEARCH ENGINE ID


# =========================
# TEXT EXPLANATION
# =========================

def explain_text(question, text, language="english", mode="student"):

    prompt = f"""
You are a science tutor.

Explain the concept clearly.

Language: {language}

Rules:
- If hinglish → mix Hindi + English
- If tanglish → mix Tamil + English
- Else → English
- Max 5 sentences

Question:
{question}

Context:
{text}

Rules:
- Use simple language
- Maximum 5 sentences
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    if "response" in data:
        return data["response"].strip()
    else:
        return "Sorry, explanation could not be generated."


# =========================
# QUIZ GENERATION
# =========================

def generate_quiz(question, context):

    prompt = f"""
Generate ONE MCQ question.

Topic:
{question}

Format EXACTLY like this:

Question: ...
A) ...
B) ...
C) ...
Correct Answer: A/B/C
"""

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    if "response" not in data:
        return {"question": "Quiz generation failed", "options": [], "answer": ""}

    text = data["response"]

    question_match = re.search(r"Question:\s*(.*)", text)
    options = re.findall(r"[A-C]\)\s*(.*)", text)
    answer_match = re.search(r"Correct Answer:\s*([A-C])", text)

    question_text = question_match.group(1) if question_match else ""
    answer_letter = answer_match.group(1) if answer_match else ""

    answer_text = ""

    if answer_letter == "A" and len(options) > 0:
        answer_text = options[0]
    elif answer_letter == "B" and len(options) > 1:
        answer_text = options[1]
    elif answer_letter == "C" and len(options) > 2:
        answer_text = options[2]

    return {
        "question": question_text,
        "options": options,
        "answer": answer_text
    }


# =========================
# DIAGRAM FLOWCHART
# =========================
def generate_diagram(question, context):

    prompt = f"""
You are an AI Science Tutor.

STRICT RULES (MUST FOLLOW):

1. Look ONLY at the QUESTION to decide language.
2. IGNORE the language of the context.
3. Answer ONLY in the SAME style as the QUESTION.
4. NEVER switch language in the middle.
5. NEVER use English if the question is in Tanglish/Tamil.
6. NEVER translate or explain meanings.
7. Output must be in ONE consistent style only.

STYLE EXAMPLES:

Input: "force na enna?"
Output: "Force na oru push illa pull. Idhu objects ah move panna use aagum."

Input: "friction na enna?"
Output: "Friction na oru force. Idhu rendu surfaces nadula oppose pannum. Slide panna kashtam aagum."

BAD:
"Friction na enna? Friction is the force..."

GOOD:
"Friction na oru force..."

Make explanation:
- very simple
- student-friendly

Question:
{question}

Context (for meaning only, NOT language):
{text}

Format:
Step1: ...
Step2: ...
Step3: ...
"""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": "llama3",
            "prompt": prompt,
            "stream": False
        }
    )

    data = response.json()

    text = data.get("response", "")

    steps = []

    for line in text.split("\n"):
        if "Step" in line:
            steps.append(line.split(":",1)[-1].strip().replace("*",""))

    if len(steps) < 3:
        steps = ["Start", "Process", "Result"]

    return {
        "nodes": [
            {"id": str(i+1), "label": steps[i]}
            for i in range(len(steps))
        ],
        "links": [
            {"source": str(i+1), "target": str(i+2)}
            for i in range(len(steps)-1)
        ]
    }



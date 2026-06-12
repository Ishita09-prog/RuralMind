from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from pdf_loader import load_all_pdfs
import os

model = SentenceTransformer("all-MiniLM-L6-v2")
text = load_all_pdfs("./ncert_books")

documents = []
paragraphs = text.split("\n\n")

for p in paragraphs:
    p = p.strip()
    if len(p) > 120:
        sentences = p.split(". ")
        chunk = ""
        for s in sentences:
            if len(chunk) + len(s) < 400:
                chunk += s + ". "
            else:
                documents.append(chunk.strip())
                chunk = s + ". "
        if chunk:
            documents.append(chunk.strip())


# Build/Load Index
dimension = 384

if os.path.exists("faiss_index.bin"):
    index = faiss.read_index("faiss_index.bin")
else:
    embeddings = model.encode(documents)
    index = faiss.IndexFlatL2(dimension)
    index.add(np.array(embeddings))
    faiss.write_index(index, "faiss_index.bin")


def retrieve_answer(query):

    query = query.lower()

    query_embedding = model.encode([query])

    distances, indices = index.search(np.array(query_embedding), 2)

    results = []

    for i in indices[0]:
        if i < len(documents):
            results.append(documents[i])

    context = " ".join(results)
    return context


# CONTEXT FILTER (separate function)
def filter_context(question, text):

    keywords = question.lower().split()
    sentences = text.split(".")

    relevant = []

    for s in sentences:
        for k in keywords:
            if k in s.lower():
                relevant.append(s.strip())
                break

    if relevant:
        return ". ".join(relevant)

    return text


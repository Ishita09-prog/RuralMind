from pypdf import PdfReader
import os

def load_all_pdfs(folder):

    all_text = ""

    for file in os.listdir(folder):

        if file.endswith(".pdf"):

            reader = PdfReader(os.path.join(folder, file))

            for page in reader.pages:

                text = page.extract_text()

                if text:
                    all_text += text + "\n"

    return all_text

import fitz  # 

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    text = []
    with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf:
        for page in pdf:
            text.append(page.get_text())
    return "\n".join(text)

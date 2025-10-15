import fitz  # PyMuPDF

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract readable text from a PDF file."""
    text = ""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text")
    except Exception as e:
        print("PDF extraction error:", e)
        return ""
    return text.strip()

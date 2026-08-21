import fitz
def extract_pdf_text(path):
    doc=fitz.open(path); return '\n'.join(f'\n--- PAGE {i+1} ---\n{p.get_text("text")}' for i,p in enumerate(doc)).strip()

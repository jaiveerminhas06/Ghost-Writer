"""Plain text out of an uploaded .txt, .docx or .pdf file. Every failure becomes an ApiError with a sentence for the page."""
import io
from pathlib import PurePath

from . import settings
from .errors import ApiError

SUPPORTED = (".txt", ".docx", ".pdf")


def _txt(data):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _docx(data):
    from docx import Document
    doc = Document(io.BytesIO(data))
    paras = [p.text.strip() for p in doc.paragraphs]
    return "\n\n".join(p for p in paras if p)


def _pdf(data):
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    if reader.is_encrypted:
        raise ApiError(422, "unreadable", "This PDF is password-protected, so its text can't be read.")
    pages = [(page.extract_text() or "").strip() for page in reader.pages[:settings.MAX_PDF_PAGES]]
    return "\n\n".join(p for p in pages if p)


def extract_text(name, data):
    """Return the text of one file, or raise ApiError(code, sentence)."""
    ext = PurePath(name).suffix.lower()
    if ext not in SUPPORTED:
        raise ApiError(422, "unsupported_file", f"{ext or 'This kind of file'} files can't be read. Use .docx, .pdf or .txt.")
    if len(data) > settings.MAX_FILE_BYTES:
        raise ApiError(413, "too_large", f"This file is larger than {settings.MAX_FILE_BYTES // (1024 * 1024)} MB.")
    try:
        text = {".txt": _txt, ".docx": _docx, ".pdf": _pdf}[ext](data).strip()
    except ApiError:
        raise
    except Exception:
        raise ApiError(422, "unreadable", "This file couldn't be opened. It may be damaged.") from None
    if not text:
        raise ApiError(422, "no_text", "No text found" + (" in the file. Scanned pages are images; the detector can't read them." if ext == ".pdf" else " in the file."))
    return text

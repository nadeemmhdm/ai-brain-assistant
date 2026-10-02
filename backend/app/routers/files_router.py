import io, json, os
from fastapi import APIRouter, Request, HTTPException

router = APIRouter(prefix="/api/files", tags=["files"])
TEXT_EXT = {".txt",".md",".markdown",".csv",".json",".py",".js",".ts",".tsx",".jsx",".html",".css",".xml",".yaml",".yml",".log"}
MAX_BYTES = 12 * 1024 * 1024
MAX_TEXT = 120_000

@router.post("/analyze")
async def analyze_file(request: Request):
    name = os.path.basename(request.headers.get("X-Filename","").replace("\\","/")).strip()
    if not name: raise HTTPException(400, "Missing file name")
    raw = await request.body()
    if not raw or len(raw) > MAX_BYTES: raise HTTPException(400, "File must be between 1 byte and 12 MB")
    ext = os.path.splitext(name)[1].lower()
    text = ""
    if ext in TEXT_EXT:
        text = raw.decode("utf-8", errors="replace")
    elif ext == ".pdf":
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(raw))
            text = "\n\n".join((p.extract_text() or "") for p in reader.pages[:80])
        except ImportError:
            raise HTTPException(409, "PDF analysis needs pypdf. Install backend requirements and restart.")
        except Exception:
            raise HTTPException(400, "Could not read this PDF.")
    else:
        raise HTTPException(415, "Supported files: PDF, TXT, Markdown, CSV, JSON, source-code and text files.")
    text = text.replace("\x00","").strip()
    if not text: raise HTTPException(400, "No readable text was found in this file.")
    clipped = len(text) > MAX_TEXT
    return {"name":name,"size":len(raw),"text":text[:MAX_TEXT],"truncated":clipped}

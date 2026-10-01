from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import translate

router = APIRouter(prefix="/api/translate", tags=["translate"])

@router.get("/status")
def status():
    return {"available": translate.available(), "installed": translate.installed_pairs(),
            "languages": translate.COMMON_LANGUAGES, "installing": translate.install_status()}

@router.get("/catalog")
def catalog():
    return translate.catalog()

class InstallBody(BaseModel):
    from_code: str
    to_code: str

@router.post("/install")
def install(body: InstallBody):
    try:
        translate.install(body.from_code, body.to_code)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True}

class TranslateBody(BaseModel):
    text: str
    from_code: str = "en"
    to_code: str

@router.post("")
def do_translate(body: TranslateBody):
    if not body.text.strip():
        raise HTTPException(400, "Nothing to translate.")
    try:
        return {"text": translate.translate(body.text, body.from_code, body.to_code)}
    except ValueError as e:
        raise HTTPException(400, str(e))

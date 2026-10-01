"""
Offline machine translation via Argos Translate -- an open-source engine
(the same one LibreTranslate is built on) that runs fully locally once a
language pair is downloaded. No cloud API, no key.

Everything here is lazily imported so the rest of the backend works with
zero extra downloads until translation is actually used. Install with:
  pip install -r backend/requirements-translate.txt
"""
import threading
from . import db

_INSTALLING: dict[str, dict] = {}   # "from>to" -> {"status": "running"|"completed"|"failed", "error": str|None}

COMMON_LANGUAGES = {
    "en": "English", "es": "Spanish", "fr": "French", "de": "German", "it": "Italian",
    "pt": "Portuguese", "ru": "Russian", "zh": "Chinese", "ja": "Japanese", "ko": "Korean",
    "ar": "Arabic", "hi": "Hindi", "ml": "Malayalam", "ta": "Tamil", "te": "Telugu",
    "bn": "Bengali", "ur": "Urdu", "tr": "Turkish", "nl": "Dutch", "pl": "Polish",
    "id": "Indonesian", "vi": "Vietnamese", "th": "Thai", "uk": "Ukrainian", "fa": "Persian",
}
NAME_TO_CODE = {v.lower(): k for k, v in COMMON_LANGUAGES.items()}
NAME_TO_CODE.update({  # a few common alternate spellings/endonyms
    "mandarin": "zh", "chinese (simplified)": "zh", "farsi": "fa", "malayalam": "ml",
})

def available() -> bool:
    try:
        import argostranslate.translate  # noqa: F401
        return True
    except ImportError:
        return False

def _pkg():
    import argostranslate.package
    return argostranslate.package

def installed_pairs() -> list[dict]:
    if not available():
        return []
    return [{"from_code": p.from_code, "from_name": p.from_name, "to_code": p.to_code, "to_name": p.to_name}
            for p in _pkg().get_installed_packages()]

def catalog() -> list[dict]:
    """The full remote package list (needs internet the first time; Argos caches its index locally after that)."""
    if not available():
        return []
    p = _pkg()
    p.update_package_index()
    have = {(x.from_code, x.to_code) for x in p.get_installed_packages()}
    return [{"from_code": x.from_code, "from_name": x.from_name, "to_code": x.to_code, "to_name": x.to_name,
             "installed": (x.from_code, x.to_code) in have}
            for x in p.get_available_packages()]

def install(from_code: str, to_code: str):
    if not available():
        raise ValueError("Translation isn't installed. Run: pip install -r backend/requirements-translate.txt")
    key = f"{from_code}>{to_code}"
    if _INSTALLING.get(key, {}).get("status") == "running":
        return
    _INSTALLING[key] = {"status": "running", "error": None}

    def work():
        try:
            p = _pkg()
            p.update_package_index()
            match = next((x for x in p.get_available_packages() if x.from_code == from_code and x.to_code == to_code), None)
            if not match:
                raise ValueError(f"No package for {from_code} -> {to_code}")
            path = match.download()
            p.install_from_path(path)
            _INSTALLING[key] = {"status": "completed", "error": None}
        except Exception as e:
            _INSTALLING[key] = {"status": "failed", "error": str(e)[:300]}

    threading.Thread(target=work, daemon=True).start()

def install_status() -> dict:
    return _INSTALLING

def resolve_code(name_or_code: str) -> str | None:
    s = name_or_code.strip().lower()
    if s in COMMON_LANGUAGES:
        return s
    return NAME_TO_CODE.get(s)

def translate(text: str, from_code: str, to_code: str) -> str:
    if not available():
        raise ValueError("Translation isn't installed. Run: pip install -r backend/requirements-translate.txt")
    if from_code == to_code:
        return text
    have = {(p["from_code"], p["to_code"]) for p in installed_pairs()}
    if (from_code, to_code) not in have:
        # Argos can chain through English if both legs are installed even without a direct pair.
        if from_code != "en" and to_code != "en" and (from_code, "en") in have and ("en", to_code) in have:
            pass
        else:
            raise ValueError(
                f"No local language pack for {COMMON_LANGUAGES.get(from_code, from_code)} -> "
                f"{COMMON_LANGUAGES.get(to_code, to_code)} yet. Install it in Models -> Translate."
            )
    import argostranslate.translate as t
    return t.translate(text, from_code, to_code)

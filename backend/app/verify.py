"""Cheap, deterministic answer checks (no extra model call)."""
import re

_NUM = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?%?")

def unsupported_numbers(answer: str, context: str) -> list[str]:
    """Numbers/years stated in the answer that appear nowhere in the sources."""
    ctx = re.sub(r"[,\s]", "", context)
    bad = []
    for m in _NUM.findall(re.sub(r"\[\d{1,2}\]", "", answer)):
        n = m.replace(",", "")
        if len(n.rstrip("%")) < 2:        # ignore single digits ("2 options")
            continue
        if n not in ctx and n not in bad:
            bad.append(m)
    return bad[:5]

import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def current() -> str:
    try:
        return open(os.path.join(ROOT, "VERSION"), encoding="utf-8").read().strip()
    except OSError:
        return "0.0.0"

def parse(v: str):
    """'v0.3.0-beta.2' -> ((0,3,0), is_final, beta_number). Final releases sort above betas."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)(?:-[a-z]+\.(\d+))?$", v.strip())
    if not m:
        return None
    major, minor, patch, pre = m.groups()
    return ((int(major), int(minor), int(patch)), pre is None, int(pre or 0))

def is_newer(candidate: str, base: str) -> bool:
    a, b = parse(candidate), parse(base)
    return bool(a and b and a > b)

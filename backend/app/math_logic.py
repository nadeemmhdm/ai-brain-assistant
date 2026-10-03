"""Deterministic local math + logic helpers. No eval, no network, no LLM arithmetic."""
import ast, math, operator, re
from fractions import Fraction

OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,
     ast.FloorDiv:operator.floordiv,ast.Mod:operator.mod,ast.Pow:operator.pow}
UOPS={ast.UAdd:operator.pos,ast.USub:operator.neg}
ARITH=re.compile(r"^[\s\d().,+\-*/%^]+$")
EQUATION=re.compile(r"^\s*([+-]?(?:\d+(?:\.\d+)?)?)\s*([a-zA-Z])\s*([+-]\s*\d+(?:\.\d+)?)?\s*=\s*([+-]?\d+(?:\.\d+)?)\s*$")

def _walk(n):
    if isinstance(n,ast.Expression): return _walk(n.body)
    if isinstance(n,ast.Constant) and type(n.value) in (int,float): return n.value
    if isinstance(n,ast.BinOp) and type(n.op) in OPS:
        a,b=_walk(n.left),_walk(n.right)
        if isinstance(n.op,ast.Pow) and (abs(b)>12 or abs(a)>1e9): raise ValueError("unsafe exponent")
        return OPS[type(n.op)](a,b)
    if isinstance(n,ast.UnaryOp) and type(n.op) in UOPS: return UOPS[type(n.op)](_walk(n.operand))
    raise ValueError("unsupported expression")

def calculate(text:str):
    raw=text.strip().lower().replace("^","**").replace(",","")
    raw=re.sub(r"^(what is|calculate|solve)\s+","",raw).rstrip(" ?=")
    pct=re.fullmatch(r"([+-]?\d+(?:\.\d+)?)\s*%\s*(?:of|\*)\s*([+-]?\d+(?:\.\d+)?)",raw)
    if pct:
        a,b=map(float,pct.groups()); return {"kind":"math","answer":a*b/100,"expression":text}
    eq=EQUATION.fullmatch(raw.replace(" ",""))
    if eq:
        a_s,var,b_s,c_s=eq.groups(); a=-1.0 if a_s=="-" else (1.0 if a_s in ("","+") else float(a_s)); b=float((b_s or "0").replace(" ","")); cc=float(c_s)
        if a==0: raise ValueError("coefficient cannot be zero")
        return {"kind":"equation","answer":(cc-b)/a,"variable":var,"expression":text}
    if not ARITH.fullmatch(raw.replace("**","^")): return None
    val=_walk(ast.parse(raw,mode="eval"))
    if isinstance(val,float) and (math.isnan(val) or math.isinf(val)): raise ValueError("non-finite result")
    return {"kind":"math","answer":val,"expression":text}

def logic_context(text:str):
    """Give the LLM a compact verification protocol for explicit logic/reasoning tasks."""
    q=text.lower()
    cues=("logic","logically","deduce","infer","constraint","puzzle","if ","therefore","prove","reason")
    if not any(x in q for x in cues): return None
    return ("LOGIC SOLVER MODE: extract premises and constraints; separate facts from assumptions; "
            "test candidate conclusions against every constraint; check contradictions and edge cases; "
            "then give only the concise reasoning summary and conclusion. Do not invent a missing premise.")

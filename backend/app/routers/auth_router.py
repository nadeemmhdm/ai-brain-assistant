from fastapi import APIRouter, Header
from pydantic import BaseModel
from .. import auth

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/status")
def status():
    return {"configured": auth.is_configured()}

class PasswordBody(BaseModel):
    password: str

@router.post("/setup")
def setup(body: PasswordBody):
    auth.setup_password(body.password)
    token = auth.login(body.password)
    return {"token": token}

@router.post("/login")
def login(body: PasswordBody):
    token = auth.login(body.password)
    return {"token": token}

class ChangePasswordBody(BaseModel):
    current: str
    new: str

@router.post("/change")
def change(body: ChangePasswordBody):
    auth.change_password(body.current, body.new)
    token = auth.login(body.new)
    return {"token": token}

@router.post("/remove")
def remove(body: PasswordBody):
    auth.remove_password(body.password)
    return {"ok": True}

@router.post("/logout")
async def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        auth.logout(authorization[len("Bearer "):])
    return {"ok": True}

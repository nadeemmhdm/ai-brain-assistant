import asyncio
from fastapi import HTTPException
from app import auth
from app.routers import teacher_router

def test_teacher_contract_imports():
    from app import teacher_mode
    assert callable(teacher_mode.lesson)
    assert callable(teacher_mode.curriculum)
    assert teacher_router.Curriculum(topic="x").topic == "x"

def test_app_lock_minimum_length():
    assert auth.MIN_PASSPHRASE_LENGTH >= 10

def test_failed_login_throttle_constants():
    assert auth.MAX_FAILED_LOGINS > 0
    assert auth.LOGIN_WINDOW_SECONDS > 0

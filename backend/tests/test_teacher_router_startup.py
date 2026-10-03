def test_teacher_router_imports_with_curriculum_contract():
    from app import teacher_mode
    from app.routers import teacher_router

    assert callable(teacher_mode.lesson)
    assert callable(teacher_mode.curriculum)
    body = teacher_router.Curriculum(topic="Python")
    assert body.topic == "Python"

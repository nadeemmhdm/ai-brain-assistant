from app import teacher_mode

def test_confidence_grades():
    assert teacher_mode.confidence_grade(90)=="A"
    assert teacher_mode.confidence_grade(75)=="B"
    assert teacher_mode.confidence_grade(60)=="C"
    assert teacher_mode.confidence_grade(30)=="D"

def test_bounded_plan_is_exactly_five():
    plan={"subtopics":[
        {"name":f"Area {i}","question":f"Explain area {i}?"} for i in range(1,7)
    ]}
    out=teacher_mode._bounded_plan(plan,"Example")
    assert len(out)==5
    assert [x["name"] for x in out]==["Area 1","Area 2","Area 3","Area 4","Area 5"]

def test_bounded_plan_rejects_fewer_than_five():
    plan={"subtopics":[{"name":"Only one","question":"Explain it?"}]}
    try:
        teacher_mode._bounded_plan(plan,"Example")
        assert False, "expected RuntimeError"
    except RuntimeError as exc:
        assert "exactly 5" in str(exc)

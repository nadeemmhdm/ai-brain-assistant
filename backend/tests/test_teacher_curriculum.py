from app import teacher_mode

def test_confidence_grades():
    assert teacher_mode.confidence_grade(90)=="A"
    assert teacher_mode.confidence_grade(75)=="B"
    assert teacher_mode.confidence_grade(60)=="C"
    assert teacher_mode.confidence_grade(30)=="D"

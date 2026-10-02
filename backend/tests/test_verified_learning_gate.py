from app import learn

def test_new_learning_session_tracks_strict_gate():
    s = learn._new_state("example")
    assert s["verified_items"] == 0
    assert s["rejected_items"] == 0
    assert s["learning_stage"] == 1
    assert s["conflicts"] == 0

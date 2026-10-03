from app import research

def test_temporal_detection():
    assert research.needs_fresh_web("latest Python release")
    assert research.needs_fresh_web("ഇപ്പോഴത്തെ പ്രധാനമന്ത്രി ആരാണ്?")
    assert research.needs_fresh_web("ippo current version etha")
    assert not research.needs_fresh_web("explain binary search")

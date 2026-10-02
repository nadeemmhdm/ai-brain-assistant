from app import dataset, cloud_training

def test_cloud_distill_defaults_to_derived_copy(monkeypatch):
    assert cloud_training.distill_dataset.__defaults__ == (True,)

def test_training_provider_catalog_has_single_active_contract():
    status = cloud_training.status()
    assert sum(1 for p in status["providers"] if p["active"]) <= 1

import pytest
from app import teacher_mode

@pytest.mark.asyncio
async def test_failed_final_review_is_not_saved(monkeypatch):
    async def local(*a,**k): return "student answer"
    reviews=iter([
      {"correct":False,"feedback":"fix this","corrected_answer":"better"},
      {"verified":False,"feedback":"still wrong","canonical_answer":""},
    ])
    monkeypatch.setattr(teacher_mode.llm_client,"complete",local)
    monkeypatch.setattr(teacher_mode,"_cloud_json",lambda *a,**k:next(reviews))
    monkeypatch.setattr(teacher_mode.cloud_training,"status",lambda:{"active_provider":"test"})
    called=[]
    monkeypatch.setattr(teacher_mode.brain,"add_knowledge",lambda *a,**k:called.append(1))
    r=await teacher_mode.lesson("topic","question")
    assert not r["verified"]
    assert not called

@pytest.mark.asyncio
async def test_verified_final_review_saves_teacher_provenance(monkeypatch):
    async def local(*a,**k): return "correct"
    reviews=iter([
      {"correct":True,"feedback":"good","corrected_answer":"correct"},
      {"verified":True,"feedback":"verified","canonical_answer":"canonical"},
    ])
    monkeypatch.setattr(teacher_mode.llm_client,"complete",local)
    monkeypatch.setattr(teacher_mode,"_cloud_json",lambda *a,**k:next(reviews))
    monkeypatch.setattr(teacher_mode.cloud_training,"status",lambda:{"active_provider":"test"})
    saved=[]
    monkeypatch.setattr(teacher_mode.brain,"add_knowledge",lambda *a,**k:saved.append((a,k)) or "kid")
    r=await teacher_mode.lesson("topic","question")
    assert r["verified"] and r["brain_id"]=="kid"
    assert saved[0][1]["verification_status"]=="teacher_verified"

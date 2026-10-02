from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import cloud_training

router=APIRouter(prefix="/api/training/cloud",tags=["training"])

class ConfigBody(BaseModel):
    provider:str
    active:bool=False
    model:str=""
    base_url:str=""
    api_key:str|None=None

@router.get("/providers")
def providers(): return cloud_training.status()

@router.put("/providers")
def configure(body:ConfigBody):
    try: return cloud_training.configure(body.provider,active=body.active,model=body.model,base_url=body.base_url,api_key=body.api_key)
    except ValueError as e: raise HTTPException(400,str(e))

@router.delete("/providers/{provider}/key")
def clear_key(provider:str):
    try: cloud_training.clear_key(provider); return {"ok":True}
    except ValueError as e: raise HTTPException(400,str(e))

class DistillBody(BaseModel): dataset_id:str

@router.post("/distill")
def distill(body:DistillBody):
    try: return cloud_training.distill_dataset(body.dataset_id)
    except RuntimeError as e: raise HTTPException(409,str(e))
    except Exception as e: raise HTTPException(502,f"Cloud training provider failed: {type(e).__name__}")

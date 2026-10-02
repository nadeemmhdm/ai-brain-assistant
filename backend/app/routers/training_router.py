from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import training, errors

router = APIRouter(prefix="/api/training", tags=["training"])

class StartTrainingBody(BaseModel):
    dataset_id: str
    base_model_path: str
    output_dir: str
    epochs: int = 3
    learning_rate: float = 2e-4
    lora_r: int = 8
    lora_alpha: int = 16
    batch_size: int = 1

@router.post("/start")
def start(body: StartTrainingBody):
    hp = {
        "epochs": body.epochs, "learning_rate": body.learning_rate,
        "lora_r": body.lora_r, "lora_alpha": body.lora_alpha, "batch_size": body.batch_size,
    }
    job_id = training.start_job(body.dataset_id, body.base_model_path, body.output_dir, hp)
    return {"job_id": job_id}

@router.get("/status")
def status(job_id: str):
    s = training.get_status(job_id)
    if not s:
        raise errors.http(404, "AIB-TRN-001", "Unknown training job.")
    return s

@router.get("")
def list_all():
    return training.list_jobs()

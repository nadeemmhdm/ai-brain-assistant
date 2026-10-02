from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from .. import training, errors, cloud_training

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
    training_mode: str = "local"  # local | cloud_assisted

@router.post("/start")
def start(body: StartTrainingBody):
    if body.training_mode not in ("local", "cloud_assisted"):
        raise errors.http(400, "AIB-TRN-001", "training_mode must be local or cloud_assisted.")
    dataset_id = body.dataset_id
    cloud_meta = None
    if body.training_mode == "cloud_assisted":
        try:
            cloud_meta = cloud_training.distill_dataset(body.dataset_id, create_copy=True)
            dataset_id = cloud_meta["dataset_id"]
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        except Exception as e:
            raise HTTPException(502, f"Cloud teacher failed before local training: {type(e).__name__}")
    hp = {
        "epochs": body.epochs, "learning_rate": body.learning_rate,
        "lora_r": body.lora_r, "lora_alpha": body.lora_alpha, "batch_size": body.batch_size,
    }
    hp["training_mode"] = body.training_mode
    if cloud_meta:
        hp["cloud_provider"] = cloud_meta.get("provider")
        hp["source_dataset_id"] = body.dataset_id
    job_id = training.start_job(dataset_id, body.base_model_path, body.output_dir, hp)
    return {"job_id": job_id, "training_mode": body.training_mode, "dataset_id": dataset_id,
            "cloud_refinement": cloud_meta}

@router.get("/status")
def status(job_id: str):
    s = training.get_status(job_id)
    if not s:
        raise errors.http(404, "AIB-TRN-001", "Unknown training job.")
    return s

@router.get("")
def list_all():
    return training.list_jobs()

from fastapi import APIRouter, HTTPException
import os
from pydantic import BaseModel
from .. import training, errors, cloud_training, dataset
from ..config import settings

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

@router.get("/models")
def training_models():
    """Discover local HuggingFace checkpoints that can actually be LoRA-trained."""
    roots = []
    for root in (settings.models_dir, os.path.join(os.path.dirname(settings.models_dir), "training-models")):
        root = os.path.abspath(os.path.expanduser(root))
        if os.path.isdir(root) and root not in roots:
            roots.append(root)
    found = []
    seen = set()
    for root in roots:
        candidates = [root]
        try:
            candidates += [os.path.join(root, n) for n in os.listdir(root)]
        except OSError:
            pass
        for p in candidates:
            if p in seen or not os.path.isdir(p):
                continue
            seen.add(p)
            if os.path.isfile(os.path.join(p, "config.json")) and (
                os.path.isfile(os.path.join(p, "model.safetensors"))
                or os.path.isfile(os.path.join(p, "pytorch_model.bin"))
                or os.path.isfile(os.path.join(p, "model.safetensors.index.json"))
                or os.path.isfile(os.path.join(p, "pytorch_model.bin.index.json"))
            ):
                found.append({"name": os.path.basename(p), "path": p})
    return found

@router.post("/start")
def start(body: StartTrainingBody):
    if body.training_mode not in ("local", "cloud_assisted"):
        raise errors.http(400, "AIB-TRN-001", "training_mode must be local or cloud_assisted.")
    approved = dataset.export_jsonl(body.dataset_id)
    if not approved:
        raise errors.http(400, "AIB-TRN-002", "Selected dataset has no approved examples.")
    base_path = os.path.abspath(os.path.expanduser(body.base_model_path))
    if not os.path.isfile(os.path.join(base_path, "config.json")):
        raise errors.http(400, "AIB-TRN-003", "Choose a HuggingFace-format training model folder containing config.json. GGUF chat files cannot be trained directly.")
    output_path = os.path.abspath(os.path.expanduser(body.output_dir))
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
    job_id = training.start_job(dataset_id, base_path, output_path, hp)
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

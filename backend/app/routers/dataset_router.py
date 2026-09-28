import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from .. import dataset

router = APIRouter(prefix="/api/dataset", tags=["dataset"])

class CreateDatasetBody(BaseModel):
    name: str
    topic: str | None = None
    only_verified: bool = True

@router.post("")
def create(body: CreateDatasetBody):
    result = dataset.create_dataset(body.name, body.topic, body.only_verified)
    if result["item_count"] == 0:
        raise HTTPException(400, "No matching knowledge found -- run Auto Learn on a topic first.")
    return result

@router.get("")
def list_all():
    return dataset.list_datasets()

@router.get("/{dataset_id}/items")
def items(dataset_id: str):
    return dataset.get_items(dataset_id)

class ApproveBody(BaseModel):
    approved: bool

@router.patch("/item/{item_id}")
def approve(item_id: str, body: ApproveBody):
    dataset.set_item_approved(item_id, body.approved)
    return {"ok": True}

@router.delete("/{dataset_id}")
def delete(dataset_id: str):
    dataset.delete_dataset(dataset_id)
    return {"ok": True}

@router.get("/{dataset_id}/export.jsonl")
def export(dataset_id: str):
    records = dataset.export_jsonl(dataset_id)
    body = "\n".join(json.dumps(r, ensure_ascii=False) for r in records)
    return PlainTextResponse(body, media_type="application/jsonl")

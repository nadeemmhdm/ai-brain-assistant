"""
Actual model training (spec sections 19 & 21) -- kept entirely separate
from Auto Learn / the AI Brain. This never runs automatically; the user
explicitly starts a job with a dataset and a base model.

IMPORTANT, and stated up front rather than discovered the hard way:
this trains a LoRA adapter against a HuggingFace-format base model
directory (config.json + safetensors/bin weights), NOT the quantized
.gguf files used for chat. You cannot fine-tune a GGUF file directly.
To use the result for local inference afterwards:
  1. Point `base_model_path` at the original (or a matching) HF checkpoint
     for your model -- e.g. download `Qwen/Qwen2.5-0.5B-Instruct` once.
  2. After training, merge the adapter (`merge_and_unload`) or keep it
     as a PEFT adapter.
  3. Convert to GGUF with llama.cpp's `convert-lora-to-gguf.py` /
     `convert_hf_to_gguf.py` (a separate, manual step -- this app does
     not silently do that conversion for you).

Heavy deps (torch, transformers, peft, datasets, accelerate) are lazily
imported so the rest of the backend works with none of them installed.
See backend/requirements-training.txt.
"""
import threading
import traceback
from . import db, dataset

JOBS: dict[str, dict] = {}  # job_id -> live status (mirrors the training_jobs row)

def _update(job_id: str, **patch):
    JOBS[job_id].update(patch)
    with db.get_conn() as conn:
        conn.execute(
            "UPDATE training_jobs SET status=?, progress_pct=?, current_step=?, log_tail=?, error=?, finished_at=? WHERE id=?",
            (JOBS[job_id]["status"], JOBS[job_id]["progress_pct"], JOBS[job_id]["current_step"],
             JOBS[job_id]["log_tail"], JOBS[job_id].get("error"), JOBS[job_id].get("finished_at"), job_id),
        )

def _train_worker(job_id: str, dataset_id: str, base_model_path: str, output_dir: str, hp: dict):
    try:
        _update(job_id, status="running", current_step="Loading dependencies (torch/transformers/peft)...", progress_pct=2)
        try:
            import torch
            from datasets import Dataset
            from transformers import (
                AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer,
                DataCollatorForLanguageModeling, TrainerCallback,
            )
            from peft import LoraConfig, get_peft_model, TaskType
        except ImportError as e:
            raise RuntimeError(
                "Training dependencies aren't installed. Run: "
                "pip install -r backend/requirements-training.txt  "
                f"(missing: {e.name})"
            )

        _update(job_id, current_step="Loading base model + tokenizer...", progress_pct=8)
        tokenizer = AutoTokenizer.from_pretrained(base_model_path)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.float32 if not torch.cuda.is_available() else torch.bfloat16,
        )

        lora_cfg = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=hp.get("lora_r", 8),
            lora_alpha=hp.get("lora_alpha", 16),
            lora_dropout=hp.get("lora_dropout", 0.05),
            target_modules=hp.get("target_modules", ["q_proj", "v_proj"]),
        )
        model = get_peft_model(model, lora_cfg)

        _update(job_id, current_step="Preparing dataset...", progress_pct=15)
        records = dataset.export_jsonl(dataset_id)
        if not records:
            raise RuntimeError("Dataset has no approved items -- approve at least one item before training.")

        def fmt(r):
            prompt = f"### Instruction:\n{r['instruction']}\n\n### Input:\n{r['input']}\n\n### Response:\n{r['output']}"
            return {"text": prompt}

        hf_dataset = Dataset.from_list([fmt(r) for r in records])

        def tokenize(batch):
            out = tokenizer(batch["text"], truncation=True, max_length=hp.get("max_length", 512), padding="max_length")
            out["labels"] = out["input_ids"].copy()
            return out

        tokenized = hf_dataset.map(tokenize, batched=True, remove_columns=["text"])

        class ProgressCallback(TrainerCallback):
            def on_step_end(self, args, state, control, **kwargs):
                if state.max_steps:
                    pct = 15 + int(80 * state.global_step / state.max_steps)
                    _update(job_id, progress_pct=min(pct, 95),
                            current_step=f"Training step {state.global_step}/{state.max_steps}",
                            log_tail=f"loss={state.log_history[-1].get('loss') if state.log_history else 'n/a'}")

        args = TrainingArguments(
            output_dir=output_dir,
            num_train_epochs=hp.get("epochs", 3),
            per_device_train_batch_size=hp.get("batch_size", 1),
            gradient_accumulation_steps=hp.get("grad_accum", 4),
            learning_rate=hp.get("learning_rate", 2e-4),
            logging_steps=1,
            save_strategy="no",
            report_to=[],
        )
        trainer = Trainer(
            model=model, args=args, train_dataset=tokenized,
            data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
            callbacks=[ProgressCallback()],
        )

        _update(job_id, current_step="Training...", progress_pct=15)
        trainer.train()

        _update(job_id, current_step="Saving adapter...", progress_pct=97)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)

        _update(job_id, status="completed", progress_pct=100,
                current_step=f"Done. LoRA adapter saved to {output_dir}. "
                              f"Convert to GGUF with llama.cpp's convert-lora-to-gguf.py to use it for local chat.",
                finished_at=db.now())
    except Exception as e:
        _update(job_id, status="failed", error=f"{e}\n{traceback.format_exc()[-1500:]}", finished_at=db.now())

def start_job(dataset_id: str, base_model_path: str, output_dir: str, hyperparams: dict) -> str:
    job_id = db.new_id()
    JOBS[job_id] = {
        "id": job_id, "dataset_id": dataset_id, "status": "queued",
        "progress_pct": 0, "current_step": "Queued", "log_tail": None, "error": None, "finished_at": None,
    }
    with db.get_conn() as conn:
        conn.execute(
            "INSERT INTO training_jobs (id, dataset_id, base_model_path, output_dir, hyperparams_json, "
            "status, progress_pct, current_step, started_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (job_id, dataset_id, base_model_path, output_dir, db.dumps(hyperparams), "queued", 0, "Queued", db.now()),
        )
    thread = threading.Thread(target=_train_worker, args=(job_id, dataset_id, base_model_path, output_dir, hyperparams), daemon=True)
    thread.start()
    return job_id

def get_status(job_id: str) -> dict | None:
    if job_id in JOBS:
        return JOBS[job_id]
    with db.get_conn() as conn:
        row = conn.execute("SELECT * FROM training_jobs WHERE id=?", (job_id,)).fetchone()
    return dict(row) if row else None

def list_jobs() -> list[dict]:
    with db.get_conn() as conn:
        rows = conn.execute("SELECT * FROM training_jobs ORDER BY started_at DESC").fetchall()
    return [dict(r) for r in rows]

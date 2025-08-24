# Root FastAPI
import os
import json
import time
import threading
import datetime as dt
from typing import Optional, Dict

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from utils.datasets import resolve_dataset, hf_download_dataset
from utils.processor import process_file_into_sft
from utils.drive_saver import DriveSaver
from utils.llm import Paraphraser
from utils.schema import CentralisedWriter

# ────────── Boot ──────────
load_dotenv(override=True)

SPACE_NAME = os.getenv("SPACE_NAME", "MedAI Processor")
OUTPUT_DIR = os.path.abspath(os.getenv("OUTPUT_DIR", "cache/outputs"))
LOG_DIR = os.path.abspath(os.getenv("LOG_DIR", "logs"))
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

drive = DriveSaver(default_folder_id=os.getenv(
    "GDRIVE_FOLDER_ID",
    "1JvW7its63E58fLxurH8ZdhxzdpcMrMbt"
))

paraphraser = Paraphraser(
    nvidia_model=os.getenv("NVIDIA_MODEL", "meta/llama-3.1-8b-instruct"),
    gemini_model_easy=os.getenv("GEMINI_MODEL_EASY", "gemini-2.5-flash-lite"),
    gemini_model_hard=os.getenv("GEMINI_MODEL_HARD", "gemini-2.5-flash"),
)

app = FastAPI(title="Medical Dataset Augmenter", version="1.1.0")

STATE_LOCK = threading.Lock()
STATE: Dict[str, object] = {
    "running": False,
    "dataset": None,
    "started_at": None,
    "progress": 0.0,
    "message": "idle",
    "last_result": None
}

class AugmentOptions(BaseModel):
    # ratios are 0..1
    paraphrase_ratio: float = 0.0
    paraphrase_outputs: bool = False
    backtranslate_ratio: float = 0.0
    style_standardize: bool = True
    deidentify: bool = True
    dedupe: bool = True
    max_chars: int = 5000                 # cap extremely long contexts
    consistency_check_ratio: float = 0.0  # small ratio e.g. 0.01
    # KD / distillation (optional, keeps default off)
    distill_fraction: float = 0.0         # for unlabeled only

class ProcessParams(BaseModel):
    augment: AugmentOptions = AugmentOptions()
    sample_limit: Optional[int] = None
    seed: int = 42

def set_state(**kwargs):
    with STATE_LOCK:
        STATE.update(kwargs)

def now_iso():
    return dt.datetime.utcnow().isoformat()

# Instructional UI
@app.get("/", response_class=HTMLResponse)
def root():
    return f"""
    <html>
    <head>
      <title>{SPACE_NAME} – Medical Dataset Augmenter</title>
      <style>
        body {{ font-family: Arial, sans-serif; max-width: 900px; margin: 2rem auto; line-height: 1.5; }}
        h1, h2 {{ color: #2c3e50; }}
        code {{ background: #f5f5f5; padding: 2px 5px; border-radius: 4px; }}
        pre {{ background: #272822; color: #f8f8f2; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
        .section {{ margin-bottom: 2rem; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 0.5rem; }}
        th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
        th {{ background: #f2f2f2; }}
      </style>
    </head>
    <body>
      <h1>📊 {SPACE_NAME} – Medical Dataset Augmenter</h1>
      <p>This Hugging Face Space processes medical QA/dialogue datasets into a <b>centralised fine-tuning format</b>
         (JSONL + CSV), with optional <i>data augmentation</i> (paraphrasing, back-translation, style standardisation, etc.).</p>

      <div class="section">
        <h2>Available Endpoints</h2>
        <table>
          <tr><th>Method</th><th>Path</th><th>Description</th></tr>
          <tr><td>GET</td><td><code>/</code></td><td>This instruction page</td></tr>
          <tr><td>POST</td><td><code>/process/{{dataset_key}}</code></td><td>Start a job (dataset_key listed below)</td></tr>
          <tr><td>GET</td><td><code>/status</code></td><td>Check current job status/progress</td></tr>
          <tr><td>GET</td><td><code>/files</code></td><td>List generated artifacts (CSV/JSONL)</td></tr>
        </table>
      </div>

      <div class="section">
        <h2>Dataset Keys</h2>
        <ul>
          <li><code>healthcaremagic</code> – 100k doctor-patient dialogues</li>
          <li><code>icliniq</code> – 10k doctor-patient dialogues</li>
          <li><code>pubmedqa_l</code> – PubMedQA labelled</li>
          <li><code>pubmedqa_u</code> – PubMedQA unlabelled</li>
          <li><code>pubmedqa_map</code> – PubMedQA triplets</li>
        </ul>
      </div>

      <div class="section">
        <h2>Example Usage with <code>curl</code></h2>
        <p>Base URL: <code>https://huggingface.co/spaces/BinKhoaLe1812/MedAI_Processing</code></p>

        <h3>1. Process HealthCareMagic (with augmentation)</h3>
        <pre>curl -X POST \\
  -H "Content-Type: application/json" \\
  -d '{{
        "augment": {{
          "paraphrase_ratio": 0.1,
          "backtranslate_ratio": 0.05,
          "paraphrase_outputs": false,
          "style_standardize": true,
          "deidentify": true,
          "dedupe": true,
          "max_chars": 5000,
          "consistency_check_ratio": 0.0
        }},
        "sample_limit": 2000,
        "seed": 42
      }}' \\
  https://huggingface.co/spaces/BinKhoaLe1812/MedAI_Processing/process/healthcaremagic
</pre>

        <h3>2. Check Status</h3>
        <pre>curl https://huggingface.co/spaces/BinKhoaLe1812/MedAI_Processing/status</pre>

        <h3>3. List Output Files</h3>
        <pre>curl https://huggingface.co/spaces/BinKhoaLe1812/MedAI_Processing/files</pre>
      </div>

      <div class="section">
        <h2>Output</h2>
        <p>Each run produces:</p>
        <ul>
          <li><b>JSONL</b> – centralised SFT format (instruction/input/output/meta)</li>
          <li><b>CSV</b> – flat format for spreadsheet inspection</li>
          <li>Both files are also uploaded automatically to Google Drive (folder ID: <code>1JvW7its63E58fLxurH8ZdhxzdpcMrMbt</code>)</li>
        </ul>
      </div>
    </body>
    </html>
    """


@app.get("/status")
def status():
    with STATE_LOCK:
        return JSONResponse(STATE)

@app.get("/files")
def files():
    out = []
    for root, _, fns in os.walk(OUTPUT_DIR):
        for fn in fns:
            out.append(os.path.relpath(os.path.join(root, fn), OUTPUT_DIR))
    return {"output_dir": OUTPUT_DIR, "files": sorted(out)}

@app.post("/process/{dataset_key}")
def process_dataset(dataset_key: str, params: ProcessParams, background: BackgroundTasks):
    with STATE_LOCK:
        if STATE["running"]:
            raise HTTPException(409, detail="Another job is running.")
        STATE["running"] = True
        STATE["dataset"] = dataset_key
        STATE["started_at"] = now_iso()
        STATE["progress"] = 0.0
        STATE["message"] = "starting"
        STATE["last_result"] = None

    background.add_task(_run_job, dataset_key, params)
    return {"ok": True, "message": f"Job for '{dataset_key}' started."}

def _run_job(dataset_key: str, params: ProcessParams):
    t0 = time.time()
    try:
        ds = resolve_dataset(dataset_key)
        if not ds:
            set_state(running=False, message="unknown dataset")
            return

        set_state(message="downloading")
        local_path = hf_download_dataset(ds["repo_id"], ds["filename"], ds["repo_type"])

        ts = dt.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        stem = f"{dataset_key}-{ts}"
        jsonl_path = os.path.join(OUTPUT_DIR, f"{stem}.jsonl")
        csv_path   = os.path.join(OUTPUT_DIR, f"{stem}.csv")

        set_state(message="processing", progress=0.05)

        writer = CentralisedWriter(jsonl_path=jsonl_path, csv_path=csv_path)
        count, stats = process_file_into_sft(
            dataset_key=dataset_key,
            input_path=local_path,
            writer=writer,
            paraphraser=paraphraser,
            augment_opts=params.augment.dict(),
            sample_limit=params.sample_limit,
            seed=params.seed,
            progress_cb=lambda p, msg=None: set_state(progress=p, message=msg or STATE["message"])
        )
        writer.close()

        set_state(message="uploading to Google Drive", progress=0.95)
        up1 = drive.upload_file_to_drive(jsonl_path, mimetype="application/json")
        up2 = drive.upload_file_to_drive(csv_path,   mimetype="text/csv")

        result = {
            "dataset": dataset_key,
            "processed_rows": count,
            "stats": stats,
            "artifacts": {"jsonl": jsonl_path, "csv": csv_path},
            "uploaded": bool(up1 and up2),
            "duration_sec": round(time.time() - t0, 2)
        }
        set_state(message="done", progress=1.0, last_result=result, running=False)

    except Exception as e:
        set_state(message=f"error: {e}", running=False)

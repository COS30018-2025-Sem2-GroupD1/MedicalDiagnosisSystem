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
        button {{
          background: #2d89ef; color: white; border: none; padding: 8px 16px;
          border-radius: 5px; cursor: pointer; margin: 5px 0;
        }}
        button:hover {{ background: #1b5dab; }}
        .section {{ margin-bottom: 2rem; }}
        #log {{ background:#f5f5f5; padding:10px; border-radius:6px; margin-top:10px; font-size:0.9rem; }}
        a {{ color:#2d89ef; text-decoration:none; }}
        a:hover {{ text-decoration:underline; }}
      </style>
    </head>
    <body>
      <h1>📊 {SPACE_NAME} – Medical Dataset Augmenter</h1>
      <p>This Hugging Face Space processes medical datasets into a <b>centralised fine-tuning format</b>
         (JSONL + CSV), with optional <i>data augmentation</i>.</p>

      <div class="section">
        <h2>⚡ Quick Actions</h2>
        <p>Click a button below to start processing a dataset with default augmentation parameters.</p>
        <button onclick="startJob('healthcaremagic')">▶ Process HealthCareMagic</button><br>
        <button onclick="startJob('icliniq')">▶ Process iCliniq</button><br>
        <button onclick="startJob('pubmedqa_l')">▶ Process PubMedQA (Labelled)</button><br>
        <button onclick="startJob('pubmedqa_u')">▶ Process PubMedQA (Unlabelled)</button><br>
        <button onclick="startJob('pubmedqa_map')">▶ Process PubMedQA (Map)</button>
      </div>

      <div class="section">
        <h2>📂 Monitoring</h2>
        <ul>
          <li><a href="/status" target="_blank">Check current job status</a></li>
          <li><a href="/files" target="_blank">List generated artifacts</a></li>
          <li><a href="https://huggingface.co/spaces/BinKhoaLe1812/MedAI_Processing/blob/main/REQUEST.md" target="_blank">📑 Request Doc (all curl examples)</a></li>
        </ul>
      </div>

      <div class="section">
        <h2>📝 Log</h2>
        <div id="log">Click a button above to run a job...</div>
      </div>

      <script>
        async function startJob(dataset) {{
          const log = document.getElementById("log");
          log.innerHTML = "⏳ Starting job for <b>" + dataset + "</b>...";
          try {{
            const resp = await fetch("/process/" + dataset, {{
              method: "POST",
              headers: {{ "Content-Type": "application/json" }},
              body: JSON.stringify({{
                augment: {{
                  paraphrase_ratio: 0.1,
                  backtranslate_ratio: 0.05,
                  paraphrase_outputs: false,
                  style_standardize: true,
                  deidentify: true,
                  dedupe: true,
                  max_chars: 5000
                }},
                sample_limit: 500,
                seed: 42
              }})
            }});
            const data = await resp.json();
            if (resp.ok) {{
              log.innerHTML = "✅ " + JSON.stringify(data);
            }} else {{
              log.innerHTML = "❌ Error: " + JSON.stringify(data);
            }}
          }} catch (err) {{
            log.innerHTML = "❌ JS Error: " + err;
          }}
        }}
      </script>
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

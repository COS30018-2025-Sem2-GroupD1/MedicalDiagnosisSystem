# HF dataset download resolver + downloader
import os
from typing import Optional
from huggingface_hub import hf_hub_download

DATASETS = {
    "healthcaremagic": {
        "repo_id":  "BinKhoaLe1812/MedDialog-EN-100k",
        "filename": "HealthCareMagic-100k.json",
        "repo_type": "dataset"
    },
    "icliniq": {
        "repo_id":  "BinKhoaLe1812/MedDialog-EN-10k",
        "filename": "iCliniq.json",
        "repo_type": "dataset"
    },
    "pubmedqa_l": {
        "repo_id":  "BinKhoaLe1812/PubMedQA-L",
        "filename": "ori_pqal.json",
        "repo_type": "dataset"
    },
    "pubmedqa_u": {
        "repo_id":  "BinKhoaLe1812/PubMedQA-U",
        "filename": "ori_pqau.json",
        "repo_type": "dataset"
    },
    "pubmedqa_map": {
        "repo_id":  "BinKhoaLe1812/PubMedQA-Map",
        "filename": "pubmed_qa_map.json",
        "repo_type": "dataset"
    }
}


def resolve_dataset(key: str) -> Optional[dict]:
    return DATASETS.get(key.lower())


def hf_download_dataset(repo_id: str, filename: str, repo_type: str = "dataset") -> str:
    path = hf_hub_download(
        repo_id=repo_id,
        filename=filename,
        repo_type=repo_type,
        local_dir=os.path.abspath("cache/hf"),
        local_dir_use_symlinks=False
    )
    return path

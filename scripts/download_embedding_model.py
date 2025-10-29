# scripts/download_embedding_model.py

import os

from huggingface_hub import snapshot_download

# Set up paths
MODEL_REPO = "abhinand/MedEmbed-large-v0.1"
MODEL_CACHE_DIR = "/app/model_cache"
HF_CACHE_DIR = os.getenv("HF_HOME", "/home/user/.cache/huggingface")

if not os.path.exists(MODEL_CACHE_DIR):
	os.makedirs(MODEL_CACHE_DIR)

print("⏳ Downloading the embedding model...")
# Download directly into /app/model_cache to avoid duplicating files from HF cache
model_path = snapshot_download(
	repo_id=MODEL_REPO,
	cache_dir=HF_CACHE_DIR,              # Store HF cache in user cache dir
	local_dir=MODEL_CACHE_DIR,           # Place usable model here
	local_dir_use_symlinks=False         # Copy files into local_dir (no symlinks)
)

print("Model path: ", model_path)

# Verify structure after moving
print("\n📂 LLM Model Structure (Build Level):")
for root, dirs, files in os.walk(MODEL_CACHE_DIR):
	print(f"📁 {root}/")
	for file in files:
		print(f"  📄 {file}")

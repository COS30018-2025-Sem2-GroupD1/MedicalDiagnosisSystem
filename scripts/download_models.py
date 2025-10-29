# scripts/download_embedding_model.py

import os

from huggingface_hub import snapshot_download

# --- Configuration ---
# Read the HF token from environment variables, essential for private models.
HUGGING_FACE_TOKEN = os.getenv("HUGGING_FACE_HUB_TOKEN", None)

# Central Hugging Face cache directory within the container.
HF_CACHE_DIR = os.getenv("HF_HOME", "/home/user/.cache/huggingface")

# Model repositories
EMBEDDING_MODEL_REPO = "abhinand/MedEmbed-large-v0.1"
LLM_REPO = "MedAI-COS30018/medalpaca-merge"

# Local directories where the final models will be stored for the app to use.
EMBEDDING_MODEL_DIR = "/app/embedding_model_cache"
LLM_DIR = "/app/llm_cache"


def download_model(repo_id: str, local_dir: str, token: str | None = None):
	"""
	Downloads a model from Hugging Face Hub to a specified local directory.

	Args:
		repo_id: The repository ID of the model on Hugging Face.
		local_dir: The application-specific directory to copy the model to.
		token: A Hugging Face token, required for private models.
	"""
	print(f"Downloading model: {repo_id}")
	if not os.path.exists(local_dir):
		os.makedirs(local_dir)

	snapshot_download(
		repo_id=repo_id,
		cache_dir=HF_CACHE_DIR,          # Use the central HF cache for downloads
		local_dir=local_dir,             # Copy final model files here
		token=token,
	)
	print(f"Model '{repo_id}' downloaded to '{local_dir}'")


if __name__ == "__main__":
	# Download the public embedding model (no token needed)
	download_model(EMBEDDING_MODEL_REPO, EMBEDDING_MODEL_DIR)

	if HUGGING_FACE_TOKEN:
		print("HUGGING_FACE_HUB_TOKEN environment variable found.")
		# WARNING: Do NOT print the full token. Just print the first few chars to confirm it's loaded.
		print(f"   Token starts with: '{HUGGING_FACE_TOKEN[:4]}...'")

		# Download the private LLM (requires a token)
		download_model(LLM_REPO, LLM_DIR, token=HUGGING_FACE_TOKEN)
	else:
		print("HUGGING_FACE_HUB_TOKEN environment variable NOT found.")

# src/services/local_llm_service.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from src.utils.logger import logger

model = None
tokeniser = None
model_loaded = False

def load_model(use_8_bit_quantise: bool = False):
	"""
	Attempts to load the model and tokenizer from the local cache.
	This function is designed to be called once during application startup.
	"""
	global model, tokeniser, model_loaded

	try:
		logger().info("Attempting to load local LLM...")
		model_path = "/app/llm_cache"
		tokeniser = AutoTokenizer.from_pretrained(model_path)
		model = AutoModelForCausalLM.from_pretrained(
			model_path,
			load_in_8bit=use_8_bit_quantise,
			device_map="auto"
		)

		model_loaded = True
		logger().info("Local LLM loaded successfully.")

	except Exception as e:
		# This will catch regular Python errors (e.g., file not found, config error).
		# It will NOT catch an OOM kill from the OS.
		logger().error(f"Failed to load local LLM: {e}", exc_info=True)
		model_loaded = False

def get_inference(prompt: str) -> str:
	"""
	Generates a response from the local model given a prompt.
	Returns an error message if the model is not available.
	"""

	if not model_loaded or not model or not tokeniser:
		logger().warning("Inference requested, but local LLM is not available.")
		return "Error: The local language model is not available."

	inputs = tokeniser(prompt, return_tensors="pt").to(model.device) # Ensure tensors are on the same device
	outputs = model.generate(**inputs)
	response = tokeniser.decode(outputs[0], skip_special_tokens=True)
	return response

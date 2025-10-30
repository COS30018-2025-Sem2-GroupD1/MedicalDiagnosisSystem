# src/services/local_llm_service.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.utils.logger import logger


# Model will be loaded once when the module is first imported.
try:
	model_loaded = True
	logger().info("Starting model loading")
	model_name = "/app/llm_cache"
	tokenizer = AutoTokenizer.from_pretrained(model_name)
	model = AutoModelForCausalLM.from_pretrained(model_name)
except Exception as e:
	logger().error("Failed to load model")
	model_loaded = False

def get_inference(prompt: str) -> str:
	"""
	Generates a response from the local model given a prompt.

	Args:
		prompt: The input text to the model.

	Returns:
		The generated text from the model.
	"""
	inputs = tokenizer(prompt, return_tensors="pt")
	outputs = model.generate(**inputs)
	response = tokenizer.decode(outputs[0], skip_special_tokens=True)
	return response

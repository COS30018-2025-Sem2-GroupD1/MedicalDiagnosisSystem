# src/services/local_llm_service.py

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Model will be loaded once when the module is first imported.
model_name = "MedAI-COS30018/medalpaca-merge"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

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

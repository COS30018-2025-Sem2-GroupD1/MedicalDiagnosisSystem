# core/memory/history.py

import json
from typing import Any

import numpy as np

from src.services.nvidia import nvidia_chat
from src.services.summariser import (summarise_qa_with_gemini,
                                     summarise_qa_with_nvidia)
from src.utils.embeddings import EmbeddingClient
from src.utils.logger import get_logger

logger = get_logger("RAG", __name__)

def _safe_json(s: str) -> Any:
	try:
		return json.loads(s)
	except Exception:
		# Try to extract a JSON object from text
		start = s.find("{")
		end = s.rfind("}")
		if start != -1 and end != -1 and end > start:
			try:
				return json.loads(s[start:end+1])
			except Exception:
				return {}
		return {}

async def files_relevance(question: str, file_summaries: list[dict[str, str]], rotator) -> dict[str, bool]:
	"""
	Ask NVIDIA model to mark each file as relevant (true) or not (false) for the question.
	Returns {filename: bool}
	"""
	sys = "You classify file relevance. Return STRICT JSON only with shape {\"relevance\":[{\"filename\":\"...\",\"relevant\":true|false}]}."
	items = [{"filename": f["filename"], "summary": f.get("summary","")} for f in file_summaries]
	user = f"Question: {question}\n\nFiles:\n{json.dumps(items, ensure_ascii=False)}\n\nReturn JSON only."
	out = await nvidia_chat(sys, user, rotator)
	data = _safe_json(out) or {}
	rels = {}
	for row in data.get("relevance", []):
		fn = row.get("filename")
		rv = row.get("relevant")
		if isinstance(fn, str) and isinstance(rv, bool):
			rels[fn] = rv
	# If parsing failed, default to considering all files possibly relevant
	if not rels and file_summaries:
		rels = {f["filename"]: True for f in file_summaries}
	return rels

def _cosine(a: np.ndarray, b: np.ndarray) -> float:
	denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1.0
	return float(np.dot(a, b) / denom)

def _as_text(block: str) -> str:
	return block.strip()

async def related_recent_and_semantic_context(user_id: str, question: str, memory, embedder: EmbeddingClient, topk_sem: int = 3) -> tuple[str, str]:
	"""
	Returns (recent_related_text, semantic_related_text).
	- recent_related_text: NVIDIA checks the last 3 summaries for direct relatedness.
	- semantic_related_text: cosine-sim search over the remaining 17 summaries (top-k).
	"""
	recent3 = memory.recent(user_id, 3)
	rest17 = memory.rest(user_id, 3)

	recent_text = ""
	if recent3:
		sys = "Pick only items that directly relate to the new question. Output the selected items verbatim, no commentary. If none, output nothing."
		numbered = [{"id": i+1, "text": s} for i, s in enumerate(recent3)]
		user = f"Question: {question}\nCandidates:\n{json.dumps(numbered, ensure_ascii=False)}\nSelect any related items and output ONLY their 'text' lines concatenated."
		key = None  # We'll let robust_post_json handle rotation via rotator param
	# Semantic over rest17
	sem_text = ""
	if rest17:
		qv = np.array(embedder.embed([question])[0], dtype="float32")
		mats = embedder.embed([_as_text(s) for s in rest17])
		sims = [(_cosine(qv, np.array(v, dtype="float32")), s) for v, s in zip(mats, rest17)]
		sims.sort(key=lambda x: x[0], reverse=True)
		top = [s for (sc, s) in sims[:topk_sem] if sc > 0.15]  # small threshold
		if top:
			sem_text = "\n\n".join(top)
	# Return recent empty (to be filled by caller using NVIDIA), and semantic text
	return ("", sem_text)

class MedicalHistoryManager:
	"""
	Enhanced medical history manager that works with the new memory system
	"""
	def __init__(self, memory, embedder: EmbeddingClient | None = None):
		self.memory = memory
		self.embedder = embedder

	async def process_medical_exchange(self, user_id: str, session_id: str, question: str, answer: str, gemini_rotator, nvidia_rotator=None) -> str:
		"""
		Process a medical Q&A exchange and store it in memory
		"""
		try:
			# Check if we have valid API keys
			if not gemini_rotator or not gemini_rotator.get_key() or gemini_rotator.get_key() == "":
				logger.info("No valid Gemini API keys available, using fallback summary")
				summary = f"q: {question}\na: {answer}"
			else:
				# Try to create summary using Gemini (preferred) or NVIDIA as fallback
				try:
					# First try Gemini
					summary = await summarise_qa_with_gemini(question, answer, gemini_rotator)
					if not summary or summary.strip() == "":
						# Fallback to NVIDIA if Gemini fails
						if nvidia_rotator and nvidia_rotator.get_key():
							summary = await summarise_qa_with_nvidia(question, answer, nvidia_rotator)
							if not summary or summary.strip() == "":
								summary = f"q: {question}\na: {answer}"
						else:
							summary = f"q: {question}\na: {answer}"
				except Exception as e:
					logger.warning(f"Failed to create AI summary: {e}")
					summary = f"q: {question}\na: {answer}"

			# Store in memory
			self.memory.add(user_id, summary)

			# Add to session history
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)

			# Update session title if it's the first message
			session = self.memory.get_session(session_id)
			if session and len(session.messages) == 2:  # Just user + assistant
				# Generate a title from the first question
				title = question[:50] + ("..." if len(question) > 50 else "")
				self.memory.update_session_title(session_id, title)

			return summary

		except Exception as e:
			logger.error(f"Error processing medical exchange: {e}")
			# Fallback: store without summary
			summary = f"q: {question}\na: {answer}"
			self.memory.add(user_id, summary)
			self.memory.add_message_to_session(session_id, "user", question)
			self.memory.add_message_to_session(session_id, "assistant", answer)
			return summary

	def get_conversation_context(self, user_id: str, session_id: str, question: str) -> str:
		"""
		Get relevant conversation context for a new question
		"""
		return self.memory.get_medical_context(user_id, session_id, question)

	def get_user_medical_history(self, user_id: str, limit: int = 10) -> list[str]:
		"""
		Get user's medical history (QA summaries)
		"""
		return self.memory.all(user_id)[-limit:]

	def search_medical_context(self, user_id: str, query: str, top_k: int = 5) -> list[str]:
		"""
		Search through user's medical context for relevant information
		"""
		if not self.embedder:
			# Fallback to simple text search
			all_context = self.memory.all(user_id)
			query_lower = query.lower()
			relevant = [ctx for ctx in all_context if query_lower in ctx.lower()]
			return relevant[:top_k]

		try:
			# Semantic search using embeddings
			query_embedding = np.array(self.embedder.embed([query])[0], dtype="float32")
			all_context = self.memory.all(user_id)

			if not all_context:
				return []

			context_embeddings = self.embedder.embed(all_context)
			similarities = []

			for i, ctx_emb in enumerate(context_embeddings):
				sim = _cosine(query_embedding, np.array(ctx_emb, dtype="float32"))
				similarities.append((sim, all_context[i]))

			# Sort by similarity and return top-k
			similarities.sort(key=lambda x: x[0], reverse=True)
			return [ctx for sim, ctx in similarities[:top_k] if sim > 0.1]

		except Exception as e:
			logger.error(f"Error in semantic search: {e}")
			# Fallback to simple search
			all_context = self.memory.all(user_id)
			query_lower = query.lower()
			relevant = [ctx for ctx in all_context if query_lower in ctx.lower()]
			return relevant[:top_k]

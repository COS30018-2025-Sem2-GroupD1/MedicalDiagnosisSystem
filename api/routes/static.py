from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def get_medical_chatbot():
	"""Serve the medical chatbot UI"""
	try:
		with open("static/index.html", "r", encoding="utf-8") as f:
			html_content = f.read()
		return HTMLResponse(content=html_content)
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Medical chatbot UI not found")

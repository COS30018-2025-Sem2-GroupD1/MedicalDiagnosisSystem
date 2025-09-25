# api/routes/static.py

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

@router.get("/system-status", response_class=HTMLResponse)
async def get_system_status():
	"""Serve the unified system status UI"""
	try:
		with open("static/system.html", "r", encoding="utf-8") as f:
			html_content = f.read()
		return HTMLResponse(content=html_content)
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="System status UI not found")

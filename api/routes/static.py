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

@router.get("/health-status", response_class=HTMLResponse)
async def get_health_status():
	"""Serve the health status UI"""
	try:
		with open("static/health.html", "r", encoding="utf-8") as f:
			html_content = f.read()
		return HTMLResponse(content=html_content)
	except FileNotFoundError:
		raise HTTPException(status_code=404, detail="Health status UI not found")

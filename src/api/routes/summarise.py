# src/api/route/summarise.py

from fastapi import APIRouter, Depends, HTTPException, status

from src.core.state import AppState, get_state
from src.models.summarise import SummariseRequest, SummariseResponse
from src.services import summariser
from src.utils.logger import logger

router = APIRouter(prefix="/summarise", tags=["Utilities"])


@router.post("", response_model=SummariseResponse)
async def summarise_text_endpoint(
	req: SummariseRequest,
	state: AppState = Depends(get_state)
):
	"""
	Summarises a given text into a short title using an available AI model.
	"""
	logger().info(f"POST /summarise for text starting with: '{req.text[:50]}...'")
	try:
		title = await summariser.summarise_title_with_nvidia(
			text=req.text,
			rotator=state.nvidia_rotator,
			max_words=req.max_words
		)
		if not title:
			raise HTTPException(
				status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
				detail="Failed to generate a summary title."
			)

		return SummariseResponse(title=title)
	except Exception as e:
		logger().error(f"Error summarising title: {e}")
		raise HTTPException(
			status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
			detail="An unexpected error occurred while generating the summary."
		)

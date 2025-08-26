from fastapi import APIRouter

from ..utils.settings import API_PATH, SETTINGS

model_route = APIRouter(
	prefix=API_PATH + "/model",
	tags=["model"]
)

@model_route.get("/student")
async def student():
	return {
		"Result" : "Works!"
	}

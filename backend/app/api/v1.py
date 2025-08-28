from fastapi import APIRouter

from app.api.routes.chat import chat_route
from app.api.routes.model import model_route
from app.api.routes.retrieval import retrieval_route

v1_route = APIRouter(
	prefix="/v1"
)

v1_route.include_router(model_route)
v1_route.include_router(chat_route)
v1_route.include_router(retrieval_route)

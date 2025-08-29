from api.v1 import v1_route
from fastapi import APIRouter
from fastapi.routing import APIRoute

api_route = APIRouter(
	prefix="/api"
)

api_route.include_router(v1_route)

@api_route.get("/", tags=["api"])
async def list_paths():
	"""Lists all paths available in the api."""
	routes: list[str] = []
	for route in v1_route.routes:
		# Check if the route is an APIRoute before accessing its path
		if isinstance(route, APIRoute):
			routes.append(route.path)

	return {
		"message:": "Welcome to the api! See the docs by redirecting to /docs or /redocs",
		"endpoints": routes
	}

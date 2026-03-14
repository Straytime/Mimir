from fastapi import FastAPI

from app.api.v1.router import api_v1_router


def create_app() -> FastAPI:
    application = FastAPI(title="mimir-api", version="v1")
    application.include_router(api_v1_router)
    return application


app = create_app()

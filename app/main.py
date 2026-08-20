"""FastAPI app factory and v1 router wiring."""

from __future__ import annotations

from fastapi import FastAPI

from app.api.v1 import auth as auth_router
from app.api.v1 import todos as todos_router


def create_app() -> FastAPI:
    app = FastAPI(title="Todo Management API", version="0.1.0")
    app.include_router(auth_router.router)
    app.include_router(todos_router.router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()


if __name__ == "__main__":  # pragma: no cover - manual launcher
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

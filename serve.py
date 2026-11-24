"""
serve.py
Production entry point: one process serves the built React app and the API.

    cd frontend && npm run build        # creates frontend/dist
    uvicorn serve:create_server --factory --host 0.0.0.0 --port 8000

The API is mounted under /api (the same paths the Vite dev proxy uses), so frontend
routes such as /history never collide with API routes.  Hashed build assets are cached
for a year; index.html is always revalidated so a new deployment is picked up at once.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.types import Scope

from api import app as api_app

DIST = Path(__file__).resolve().parent / "frontend" / "dist"


class CachedStaticFiles(StaticFiles):
    """Static files with long-lived caching for content-hashed build assets."""

    async def get_response(self, path: str, scope: Scope):
        response = await super().get_response(path, scope)
        if response.status_code == 200:
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return response


def create_server(dist: Path = DIST) -> FastAPI:
    if not (dist / "index.html").exists():
        raise RuntimeError(f"Frontend build not found at {dist}. Run `npm run build` in frontend/ first.")

    server = FastAPI(title="TwinLife AI", docs_url=None, redoc_url=None, openapi_url=None)
    server.add_middleware(GZipMiddleware, minimum_size=1024)
    server.mount("/api", api_app)
    server.mount("/assets", CachedStaticFiles(directory=dist / "assets"), name="assets")

    @server.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        # Real files from public/ (models, favicon) are served as-is; every other path is a client route.
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate, headers={"Cache-Control": "public, max-age=86400"})
        return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache"})

    return server

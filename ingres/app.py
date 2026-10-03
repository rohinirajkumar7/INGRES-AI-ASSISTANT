"""FastAPI app. All routes are served under /api (and also at the root, so the
app works whether or not the hosting layer strips the /api prefix)."""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .gemini import GeminiClient
from .service import ChatService, NotFound

service = ChatService(llm=GeminiClient())


class ChatContext(BaseModel):
    state: Optional[str] = Field(default=None, max_length=80)
    district: Optional[str] = Field(default=None, max_length=80)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    language: str = Field(default="auto", max_length=8)
    context: Optional[ChatContext] = None


router = APIRouter()


def _nf(exc: Exception) -> HTTPException:
    return HTTPException(status_code=404, detail=str(exc))


@router.post("/chat")
async def chat(req: ChatRequest) -> Dict[str, Any]:
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=422, detail="message must not be empty")
    ctx = req.context.model_dump(exclude_none=True) if req.context else {}
    try:
        return await service.chat(message, req.language, ctx)
    except NotFound as exc:
        raise _nf(exc)


@router.get("/states")
def states() -> List[str]:
    return service.states()


@router.get("/districts/{state}")
def districts(state: str) -> List[str]:
    try:
        return service.districts(state)
    except NotFound as exc:
        raise _nf(exc)


@router.get("/data/{state}")
def state_data(state: str) -> List[dict]:
    try:
        return service.state_data(state)
    except NotFound as exc:
        raise _nf(exc)


# NOTE: /stats/total must be declared BEFORE /stats/{state} or it is shadowed.
@router.get("/stats/total")
def total_stats() -> dict:
    return service.total_stats()


@router.get("/stats/{state}")
def state_stats(state: str) -> dict:
    try:
        return service.state_stats(state)
    except NotFound as exc:
        raise _nf(exc)


@router.get("/map")
def map_data() -> dict:
    return service.map_data()


@router.get("/rankings")
def rankings(metric: str = "extraction", order: str = Query("desc", pattern="^(asc|desc)$"),
             limit: int = Query(10, ge=1, le=50), state: Optional[str] = None,
             level: str = Query("district", pattern="^(district|state)$")) -> dict:
    try:
        return service.rankings(metric, order, limit, state, level)
    except NotFound as exc:
        raise _nf(exc)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/health")
def health() -> dict:
    return service.health()


def create_app() -> FastAPI:
    app = FastAPI(title="INGRES Groundwater Chatbot API", version="4.0")
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,
                       allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"])
    app.include_router(router, prefix="/api")
    app.include_router(router)
    return app


app = create_app()

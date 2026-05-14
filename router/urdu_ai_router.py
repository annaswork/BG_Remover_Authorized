import asyncio
import threading
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from controller import urdu_ai_controller as urdu
from controller.auth_controller import require_api_key

router = APIRouter(prefix="/api/urdu-shayari", tags=["urdu-shayari"])

_semaphore = threading.Semaphore(30)


class AiConversationBody(BaseModel):
    prompt: str = Field(..., description="User message to the poet / character")


def _run_sync(fn, *args, **kwargs) -> Any:
    _semaphore.acquire()
    try:
        return fn(*args, **kwargs)
    finally:
        _semaphore.release()


@router.post("/ai-conversation")
async def ai_conversation_endpoint(
    body: AiConversationBody,
    character: str = Query(..., description="Character: Urdu Scholar, Shayar, Dost, Competitor, Ustad"),
    username: str = Query(...),
    name: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    age: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    additional_data: dict[str, Any] = {
        "prompt": body.prompt,
        "character": character,
        "username": username,
    }
    if name:
        additional_data["name"] = name
    if gender:
        additional_data["gender"] = gender
    if age:
        additional_data["age"] = age

    try:
        return await asyncio.to_thread(_run_sync, urdu.ai_conversation_with_poets, additional_data)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


@router.post("/stream/ai-conversation")
async def ai_conversation_stream_endpoint(
    body: AiConversationBody,
    character: str = Query(..., description="Character: Urdu Scholar, Shayar, Dost, Competitor, Ustad"),
    username: str = Query(...),
    name: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    age: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    additional_data: dict[str, Any] = {
        "prompt": body.prompt,
        "character": character,
        "username": username,
    }
    if name:
        additional_data["name"] = name
    if gender:
        additional_data["gender"] = gender
    if age:
        additional_data["age"] = age

    try:
        urdu.ensure_openai_configured()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    return StreamingResponse(
        urdu.stream_ai_conversation(additional_data),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/stream/poetry-by-topic")
async def poetry_by_topic_stream(
    poetry_topic: str = Query(...),
    username: str = Query(...),
    _auth: dict = Depends(require_api_key),
):
    try:
        urdu.ensure_openai_configured()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    data = {"poetry_topic": poetry_topic, "username": username}
    return StreamingResponse(
        urdu.stream_poetry_by_topic(data),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/stream/poetry-by-type")
async def poetry_by_type_stream(
    poetry_type: str = Query(...),
    username: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    try:
        urdu.ensure_openai_configured()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e

    data = {"poetry_type": poetry_type, "username": username or ""}
    return StreamingResponse(
        urdu.stream_poetry_by_type(data),
        media_type="text/plain; charset=utf-8",
    )


@router.get("/chat-history")
async def get_chat_history_endpoint(
    username: str = Query(...),
    poetry_topic: Optional[str] = Query(None),
    poetry_type: Optional[str] = Query(None),
    character: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    additional_data: dict[str, Any] = {"username": username}
    if poetry_topic:
        additional_data["poetry_topic"] = poetry_topic
    if poetry_type:
        additional_data["poetry_type"] = poetry_type
    if character:
        additional_data["character"] = character
    if name:
        additional_data["name"] = name
    if gender:
        additional_data["gender"] = gender

    if not any(k in additional_data for k in ("poetry_topic", "poetry_type", "character")):
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: poetry_topic, poetry_type, or character",
        )

    return await asyncio.to_thread(_run_sync, urdu.get_chat_history, additional_data)


@router.delete("/chat-history")
async def delete_chat_history_endpoint(
    username: str = Query(...),
    character: str = Query(...),
    name: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    _auth: dict = Depends(require_api_key),
):
    additional_data: dict[str, Any] = {"username": username, "character": character}
    if name:
        additional_data["name"] = name
    if gender:
        additional_data["gender"] = gender
    return await asyncio.to_thread(_run_sync, urdu.delete_chat_history, additional_data)

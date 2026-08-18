from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..llm_agent import run_chat_turn
from ..models import store

router = APIRouter(prefix="/api/chat", tags=["chat"])

# история диалога в памяти процесса — для одного демо-пользователя этого
# достаточно; для multi-user нужно завязать на session/user id (см. roadmap)
_history: list[dict] = []


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(req: ChatRequest):
    global _history
    reply, updated_history, tool_calls = await run_chat_turn(req.message, _history)
    _history = updated_history
    # чтобы история не росла бесконечно и не разгоняла стоимость токенов
    if len(_history) > 40:
        _history = _history[-40:]
    return {
        "reply": reply,
        "tool_calls": tool_calls,
        "tasks": [t.model_dump(mode="json") for t in store.all()],
    }


@router.post("/reset")
def reset_chat():
    global _history
    _history = []
    return {"success": True}

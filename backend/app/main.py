from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv()

from .routers import chat, excel, tasks


class UTF8JSONResponse(JSONResponse):
    """Обычный JSONResponse не добавляет charset=utf-8 в заголовок Content-Type
    для application/json (это не текстовый media_type для Starlette), из-за
    чего некоторые браузеры при просмотре сырого JSON (не через fetch/JS, а
    прямым открытием ссылки) сами гадают кодировку и иногда угадывают неверно
    — получается кракозябры вместо кириллицы. Явно фиксируем charset здесь."""
    media_type = "application/json; charset=utf-8"


app = FastAPI(title="AI Gantt Planner API", default_response_class=UTF8JSONResponse)

origins = os.environ.get("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router)
app.include_router(chat.router)
app.include_router(excel.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
"""
Чат-агент.

Архитектура: инструменты определены один раз как MCP tools (app/mcp/tools.py)
через FastMCP. Здесь мы забираем их схему (имя, описание, JSON Schema
аргументов) и конвертируем в формат OpenAI function calling (OpenRouter
использует OpenAI-совместимый API поверх любой модели — Claude, GPT,
Gemini и т.д., выбор модели — это просто строка в env-переменной).

Когда модель решает вызвать инструмент (tool_calls в ответе), мы исполняем
соответствующую python-функцию из mcp/tools.py напрямую (in-process call)
и возвращаем результат модели как сообщение role="tool" — по кругу, пока
модель не выдаст финальный текстовый ответ.

Почему in-process, а не полноценный MCP-сервер по stdio/SSE: для одного
контейнера с одним клиентом это проще и надёжнее в деплое (меньше
движущихся частей). Схема инструментов при этом честно берётся из
MCP-объекта, так что переход на "настоящий" удалённый MCP-сервер (другой
процесс/контейнер) — это замена одной функции _call_tool() на MCP client
вызов. Подробнее — в Roadmap to production.
"""
from __future__ import annotations

import json
import os

from openai import OpenAI

from .mcp.tools import TOOLS

# OpenRouter отдаёт OpenAI-совместимый API, поэтому используем openai SDK,
# просто указываем ему другой base_url и ключ OpenRouter.
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
    default_headers={
        # OpenRouter просит указывать источник трафика — не обязательно,
        # но так модель в их дашборде будет подписана вашим проектом
        "HTTP-Referer": os.environ.get("APP_URL", "http://localhost:5173"),
        "X-Title": "AI Gantt Planner",
    },
)
# любая модель, доступная на OpenRouter и поддерживающая tool calling,
# например: "anthropic/claude-sonnet-4.6", "openai/gpt-4.1", "google/gemini-2.5-pro"
MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")

SYSTEM_PROMPT = """Ты — ассистент по управлению планом проекта на диаграмме Ганта.
Пользователь пишет тебе на естественном языке, что нужно поменять в плане
(перенести задачи, поменять исполнителей, добавить/удалить задачи, поменять
зависимости). Твоя задача — вызвать нужные инструменты, чтобы реально
применить изменения, а не просто описать их текстом.

Правила:
- Если пользователь ссылается на задачу по имени — используй имя как есть,
  инструменты сами найдут задачу по названию.
- Если нужно узнать текущее состояние плана перед изменением — сначала
  вызови list_tasks.
- Если запрос затрагивает несколько задач ("перенеси все задачи Петрова
  на неделю позже") — сначала list_tasks, затем вызови нужный инструмент
  по каждой подходящей задаче отдельно.
- Даты сегодня и далее указывай в формате YYYY-MM-DD.
- После выполнения изменений кратко, по-человечески опиши в ответе, что
  именно изменил (какие задачи и как) — 1-3 предложения, без списков.
- Если запрос неоднозначен или задача не найдена — переспроси, не выдумывай.
"""


def _build_openai_tools() -> list[dict]:
    """Конвертирует реестр инструментов (app/mcp/tools.py) в формат
    OpenAI/OpenRouter function calling: {"type": "function", "function": {name, description, parameters}}."""
    tools = []
    for name, tool in TOOLS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": tool["description"],
                "parameters": tool["parameters"],
            },
        })
    return tools


def _call_tool(name: str, arguments: dict):
    tool = TOOLS.get(name)
    if not tool:
        return {"error": f"Неизвестный инструмент {name}"}
    result = tool["fn"](**arguments)
    return result


async def run_chat_turn(message: str, history: list[dict]) -> tuple[str, list[dict], list[dict]]:
    """Прогоняет одно сообщение пользователя через агентный цикл (ReAct-паттерн:
    модель думает -> вызывает инструмент -> видит результат -> думает дальше).

    Возвращает (финальный_текст_ответа, обновлённая_история_сообщений,
    список_вызванных_инструментов_для_отладки_в_ui).
    """
    tools_schema = _build_openai_tools()

    if not history:
        history = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages = history + [{"role": "user", "content": message}]

    tool_calls_made = []

    for _ in range(8):  # защита от бесконечного цикла tool-calls
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools_schema,
            max_tokens=1500,
        )
        choice = response.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            # модель ответила текстом — финальный ответ, выходим из цикла
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content or "", messages, tool_calls_made

        # модель хочет вызвать один или несколько инструментов
        messages.append({
            "role": "assistant",
            "content": msg.content,
            "tool_calls": [tc.model_dump() for tc in msg.tool_calls],
        })

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = _call_tool(tc.function.name, args)
            tool_calls_made.append({"tool": tc.function.name, "input": args, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result, ensure_ascii=False, default=str),
            })
        # цикл продолжается: модель увидит tool-результаты и либо ответит
        # текстом, либо вызовет следующий инструмент

    return "Не удалось завершить обработку запроса за разумное число шагов.", messages, tool_calls_made

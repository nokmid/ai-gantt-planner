"""
Изолированный тест диалога с OpenRouter — без FastAPI, без фронта.
Запускать так:

    cd backend
    pip install openai python-dotenv
    OPENROUTER_API_KEY=sk-or-... python ../scripts/test_openrouter_chat.py

Цель: пощупать, как модель вызывает инструменты и как выглядит
финальный ответ, прежде чем разбираться в полном agent loop приложения.
"""
import json
import os

from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = os.environ.get("OPENROUTER_MODEL", "anthropic/claude-sonnet-4.6")

# один простой инструмент для теста — не весь набор из mcp/tools.py
tools = [{
    "type": "function",
    "function": {
        "name": "shift_task",
        "description": "Сдвинуть задачу на N дней вперёд или назад",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string"},
                "days": {"type": "integer"},
            },
            "required": ["task_name_or_id", "days"],
        },
    },
}]


def fake_shift_task(task_name_or_id: str, days: int) -> dict:
    """Заглушка вместо реального TaskStore — просто чтобы увидеть цикл целиком."""
    print(f"  >>> [ВЫЗВАН ИНСТРУМЕНТ] shift_task(task_name_or_id={task_name_or_id!r}, days={days})")
    return {"success": True, "task": {"name": task_name_or_id, "new_start_date": "2026-08-25"}}


def run(user_message: str):
    messages = [{"role": "user", "content": user_message}]
    print(f"\nПОЛЬЗОВАТЕЛЬ: {user_message}")

    for step in range(5):
        response = client.chat.completions.create(model=MODEL, messages=messages, tools=tools)
        msg = response.choices[0].message

        if not msg.tool_calls:
            print(f"АГЕНТ (финальный ответ): {msg.content}")
            return

        messages.append({"role": "assistant", "content": msg.content, "tool_calls": [tc.model_dump() for tc in msg.tool_calls]})
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            result = fake_shift_task(**args)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result, ensure_ascii=False)})


if __name__ == "__main__":
    run("Перенеси задачу Дизайн UI на 3 дня позже")

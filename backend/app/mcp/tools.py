"""
MCP-инструменты для управления диаграммой Ганта.

Изначально это было реализовано через библиотеку `mcp` (FastMCP), которая
сама генерирует JSON-схему аргументов из type hints. Но эта библиотека
требует Python >= 3.10, а у части машин (в т.ч. стандартный /usr/bin/python3
на Mac) стоит 3.9 — поэтому здесь та же идея реализована вручную, без
внешней зависимости: простой реестр TOOLS, где для каждой функции рядом
лежит её JSON Schema аргументов. Смысл MCP-подхода при этом не меняется:
LLM получает список этих инструментов и решает, какой вызвать — а
реальное изменение делает вот этот детерминированный python-код.

Каждый инструмент — одна атомарная операция над планом. Агент может
вызвать несколько инструментов подряд в рамках одного сообщения в чате
(например: "перенеси задачу и переназначь исполнителя" = 2 вызова).
"""
from __future__ import annotations

from datetime import date, timedelta

from ..models import Task, store


def _resolve_task(name_or_id: str) -> Task | None:
    task = store.get(name_or_id)
    if task:
        return task
    return store.get_by_name(name_or_id)


# --- сами функции-инструменты (без изменений в логике) -------------------

def list_tasks() -> list[dict]:
    return [t.model_dump(mode="json") for t in store.all()]


def move_task(task_name_or_id: str, new_start_date: str) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    updated = store.update(task.id, start_date=date.fromisoformat(new_start_date))
    return {"success": True, "task": updated.model_dump(mode="json")}


def shift_task(task_name_or_id: str, days: int) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    new_start = task.start_date + timedelta(days=days)
    updated = store.update(task.id, start_date=new_start)
    return {"success": True, "task": updated.model_dump(mode="json")}


def set_duration(task_name_or_id: str, duration_days: int) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    updated = store.update(task.id, duration_days=max(1, duration_days))
    return {"success": True, "task": updated.model_dump(mode="json")}


def reassign_task(task_name_or_id: str, new_assignee: str) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    updated = store.update(task.id, assignee=new_assignee)
    return {"success": True, "task": updated.model_dump(mode="json")}


def add_dependency(task_name_or_id: str, depends_on_name_or_id: str) -> dict:
    task = _resolve_task(task_name_or_id)
    dep = _resolve_task(depends_on_name_or_id)
    if not task or not dep:
        return {"error": "Одна из задач не найдена"}
    preds = list(set(task.predecessors + [dep.id]))
    updated = store.update(task.id, predecessors=preds)
    return {"success": True, "task": updated.model_dump(mode="json")}


def remove_dependency(task_name_or_id: str, depends_on_name_or_id: str) -> dict:
    task = _resolve_task(task_name_or_id)
    dep = _resolve_task(depends_on_name_or_id)
    if not task or not dep:
        return {"error": "Одна из задач не найдена"}
    preds = [p for p in task.predecessors if p != dep.id]
    updated = store.update(task.id, predecessors=preds)
    return {"success": True, "task": updated.model_dump(mode="json")}


def add_task(name: str, description: str = "", assignee: str = "",
             start_date: str | None = None, duration_days: int = 1,
             predecessor_names: list[str] | None = None) -> dict:
    pred_ids = []
    for n in (predecessor_names or []):
        t = _resolve_task(n)
        if t:
            pred_ids.append(t.id)
    start = date.fromisoformat(start_date) if start_date else date.today()
    task = Task(name=name, description=description, assignee=assignee,
                start_date=start, duration_days=duration_days, predecessors=pred_ids)
    store.add(task)
    return {"success": True, "task": task.model_dump(mode="json")}


def delete_task(task_name_or_id: str) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    store.delete(task.id)
    return {"success": True, "deleted_id": task.id}


def set_progress(task_name_or_id: str, progress: int) -> dict:
    task = _resolve_task(task_name_or_id)
    if not task:
        return {"error": f"Задача '{task_name_or_id}' не найдена"}
    updated = store.update(task.id, progress=max(0, min(100, progress)))
    return {"success": True, "task": updated.model_dump(mode="json")}


# --- реестр: имя -> (функция, описание, JSON Schema аргументов) ----------
# Это ровно то, что раньше генерировала библиотека `mcp` автоматически из
# докстрингов и type hints — здесь то же самое написано явно руками.

TOOLS: dict[str, dict] = {
    "list_tasks": {
        "fn": list_tasks,
        "description": "Вернуть список всех задач текущего плана с их id, названиями, "
                        "датами, исполнителями и зависимостями. Используй это в начале, если "
                        "нужно понять текущее состояние плана перед изменением.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    "move_task": {
        "fn": move_task,
        "description": "Перенести задачу на новую дату начала.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или её id"},
                "new_start_date": {"type": "string", "description": "новая дата начала в формате YYYY-MM-DD"},
            },
            "required": ["task_name_or_id", "new_start_date"],
        },
    },
    "shift_task": {
        "fn": shift_task,
        "description": "Сдвинуть задачу на N дней вперёд (положительное число) или назад "
                        "(отрицательное) относительно текущей даты начала.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или id"},
                "days": {"type": "integer", "description": "на сколько дней сдвинуть (может быть отрицательным)"},
            },
            "required": ["task_name_or_id", "days"],
        },
    },
    "set_duration": {
        "fn": set_duration,
        "description": "Изменить длительность задачи в днях.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или id"},
                "duration_days": {"type": "integer", "description": "новая длительность в днях (>= 1)"},
            },
            "required": ["task_name_or_id", "duration_days"],
        },
    },
    "reassign_task": {
        "fn": reassign_task,
        "description": "Переназначить исполнителя задачи.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или id"},
                "new_assignee": {"type": "string", "description": "имя нового исполнителя"},
            },
            "required": ["task_name_or_id", "new_assignee"],
        },
    },
    "add_dependency": {
        "fn": add_dependency,
        "description": "Добавить зависимость: задача task_name_or_id теперь не может "
                        "начаться раньше окончания depends_on_name_or_id.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "задача, которая получает зависимость"},
                "depends_on_name_or_id": {"type": "string", "description": "задача-предшественник"},
            },
            "required": ["task_name_or_id", "depends_on_name_or_id"],
        },
    },
    "remove_dependency": {
        "fn": remove_dependency,
        "description": "Убрать зависимость между двумя задачами.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "задача, у которой убираем зависимость"},
                "depends_on_name_or_id": {"type": "string", "description": "задача-предшественник, которую убираем"},
            },
            "required": ["task_name_or_id", "depends_on_name_or_id"],
        },
    },
    "add_task": {
        "fn": add_task,
        "description": "Добавить новую задачу в план.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "название задачи"},
                "description": {"type": "string", "description": "описание задачи"},
                "assignee": {"type": "string", "description": "исполнитель"},
                "start_date": {"type": "string", "description": "дата начала YYYY-MM-DD, если не указана — сегодня"},
                "duration_days": {"type": "integer", "description": "длительность в днях"},
                "predecessor_names": {
                    "type": "array", "items": {"type": "string"},
                    "description": "список названий задач-предшественников",
                },
            },
            "required": ["name"],
        },
    },
    "delete_task": {
        "fn": delete_task,
        "description": "Удалить задачу из плана.",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или id"},
            },
            "required": ["task_name_or_id"],
        },
    },
    "set_progress": {
        "fn": set_progress,
        "description": "Установить процент готовности задачи (0-100).",
        "parameters": {
            "type": "object",
            "properties": {
                "task_name_or_id": {"type": "string", "description": "название задачи или id"},
                "progress": {"type": "integer", "description": "процент готовности от 0 до 100"},
            },
            "required": ["task_name_or_id", "progress"],
        },
    },
}

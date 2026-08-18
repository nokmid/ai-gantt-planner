"""
Модели данных проекта.

Хранилище — простое in-memory (список словарей в памяти процесса) плюс
дамп в JSON-файл на диске, чтобы данные переживали перезапуск процесса
в деве. Для продакшена это нужно заменить на нормальную БД (см. roadmap).
"""
from __future__ import annotations

import json
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field

DATA_FILE = Path(__file__).parent / "data" / "tasks.json"
DATA_FILE.parent.mkdir(exist_ok=True)

_lock = threading.Lock()


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4())[:8])
    name: str
    description: str = ""
    assignee: str = ""
    start_date: date
    duration_days: int = 1
    predecessors: list[str] = Field(default_factory=list)  # список id задач
    progress: int = 0  # 0-100, для визуализации прогресса на диаграмме

    @property
    def end_date(self) -> date:
        # duration_days включает стартовый день
        return self.start_date + timedelta(days=max(self.duration_days, 1) - 1)


class TaskStore:
    """Простое потокобезопасное хранилище задач в памяти + persist в JSON."""

    def __init__(self):
        self._tasks: dict[str, Task] = {}
        self._load()

    def _load(self):
        if DATA_FILE.exists():
            raw = json.loads(DATA_FILE.read_text())
            for t in raw:
                task = Task(**t)
                self._tasks[task.id] = task

    def _persist(self):
        DATA_FILE.write_text(
            json.dumps([json.loads(t.model_dump_json()) for t in self._tasks.values()], default=str, ensure_ascii=False, indent=2)
        )

    def all(self) -> list[Task]:
        return sorted(self._tasks.values(), key=lambda t: t.start_date)

    def get(self, task_id: str) -> Optional[Task]:
        return self._tasks.get(task_id)

    def get_by_name(self, name: str) -> Optional[Task]:
        """Нечёткий поиск задачи по названию — используется агентом,
        когда пользователь в чате называет задачу по имени, а не по id."""
        name_lower = name.strip().lower()
        for t in self._tasks.values():
            if t.name.strip().lower() == name_lower:
                return t
        # частичное совпадение, если точного нет
        for t in self._tasks.values():
            if name_lower in t.name.strip().lower():
                return t
        return None

    def add(self, task: Task) -> Task:
        with _lock:
            self._tasks[task.id] = task
            self._persist()
        return task

    def update(self, task_id: str, **fields) -> Optional[Task]:
        with _lock:
            task = self._tasks.get(task_id)
            if not task:
                return None
            updated = task.model_copy(update=fields)
            self._tasks[task_id] = updated
            self._persist()
            return updated

    def delete(self, task_id: str) -> bool:
        with _lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
                # чистим ссылки на удалённую задачу у остальных
                for t in self._tasks.values():
                    if task_id in t.predecessors:
                        t.predecessors.remove(task_id)
                self._persist()
                return True
            return False

    def replace_all(self, tasks: list[Task]):
        with _lock:
            self._tasks = {t.id: t for t in tasks}
            self._persist()


def seed_data() -> list[Task]:
    today = date.today()
    t1 = Task(id="t1", name="Исследование рынка", description="Анализ конкурентов и целевой аудитории",
               assignee="Иванова А.", start_date=today, duration_days=3, progress=100)
    t2 = Task(id="t2", name="Прототип UX", description="Wireframes ключевых экранов",
               assignee="Петров С.", start_date=today + timedelta(days=3), duration_days=4,
               predecessors=["t1"], progress=60)
    t3 = Task(id="t3", name="Дизайн UI", description="Финальные макеты в Figma",
               assignee="Сидорова М.", start_date=today + timedelta(days=7), duration_days=5,
               predecessors=["t2"], progress=20)
    t4 = Task(id="t4", name="Backend API", description="FastAPI + БД + auth",
               assignee="Кузнецов Д.", start_date=today + timedelta(days=3), duration_days=8,
               predecessors=["t1"], progress=40)
    t5 = Task(id="t5", name="Frontend разработка", description="React-приложение по макетам",
               assignee="Петров С.", start_date=today + timedelta(days=12), duration_days=7,
               predecessors=["t3", "t4"], progress=0)
    t6 = Task(id="t6", name="Интеграционное тестирование", description="E2E тесты основных сценариев",
               assignee="Смирнова Е.", start_date=today + timedelta(days=19), duration_days=3,
               predecessors=["t5"], progress=0)
    t7 = Task(id="t7", name="Релиз", description="Деплой в продакшн, мониторинг",
               assignee="Кузнецов Д.", start_date=today + timedelta(days=22), duration_days=1,
               predecessors=["t6"], progress=0)
    return [t1, t2, t3, t4, t5, t6, t7]


store = TaskStore()
if not store.all():
    for t in seed_data():
        store.add(t)

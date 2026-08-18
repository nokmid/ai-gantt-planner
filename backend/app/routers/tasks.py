from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..models import Task, store

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
def list_tasks():
    return [t.model_dump(mode="json") for t in store.all()]


@router.post("")
def create_task(task: Task):
    store.add(task)
    return task.model_dump(mode="json")


@router.patch("/{task_id}")
def patch_task(task_id: str, fields: dict):
    updated = store.update(task_id, **fields)
    if not updated:
        raise HTTPException(404, "Задача не найдена")
    return updated.model_dump(mode="json")


@router.delete("/{task_id}")
def remove_task(task_id: str):
    ok = store.delete(task_id)
    if not ok:
        raise HTTPException(404, "Задача не найдена")
    return {"success": True}

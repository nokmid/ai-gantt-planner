from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO

from ..excel_service import export_excel, parse_excel
from ..models import store

router = APIRouter(prefix="/api/excel", tags=["excel"])


@router.post("/import")
async def import_excel(file: UploadFile = File(...)):
    content = await file.read()
    try:
        tasks = parse_excel(content)
    except Exception as e:
        raise HTTPException(400, f"Не удалось разобрать файл: {e}")
    store.replace_all(tasks)
    return {"success": True, "count": len(tasks), "tasks": [t.model_dump(mode="json") for t in tasks]}


@router.get("/export")
def export():
    data = export_excel(store.all())
    return StreamingResponse(
        BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=gantt_plan.xlsx"},
    )

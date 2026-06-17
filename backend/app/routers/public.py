"""Публичные эндпоинты для share-ссылок (без авторизации)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Activity, Route

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/activities/{share_token}")
def public_activity(share_token: str, db: Session = Depends(get_db)) -> dict:
    activity = db.scalar(select(Activity).where(Activity.share_token == share_token))
    if not activity or not activity.is_public:
        raise HTTPException(status_code=404, detail="Отчёт недоступен")
    route_name = None
    if activity.route_id:
        route = db.get(Route, activity.route_id)
        route_name = route.name if route else None
    return {
        "id": activity.id,
        "name": activity.name,
        "athlete": activity.athlete.name,
        "route_name": route_name,
        "recorded_at": activity.recorded_at.isoformat() if activity.recorded_at else None,
        "report": activity.report,
    }

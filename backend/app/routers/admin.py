"""Админ-API: сводный просмотр и администрирование всех данных (Basic auth)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Activity, Athlete, RegistrationRequest, Route
from ..security import require_admin
from ..services.athletes import create_athlete

router = APIRouter(prefix="/api/admin", tags=["admin"],
                   dependencies=[Depends(require_admin)])


@router.get("/login")
def login() -> dict:
    """Проверка учётки админа (вызов с Basic-заголовком)."""
    return {"ok": True}


@router.get("/routes")
def all_routes(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Route).order_by(Route.updated_at.desc())).all()
    out = []
    for r in rows:
        out.append({
            **r.to_summary(),
            "athlete_id": r.athlete_id,
            "athlete": r.athlete.name if r.athlete else None,
        })
    return out


@router.delete("/routes/{route_id}")
def delete_route(route_id: str, db: Session = Depends(get_db)) -> dict:
    route = db.get(Route, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Маршрут не найден")
    db.delete(route)
    db.commit()
    return {"deleted": route_id}


@router.get("/activities")
def all_activities(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Activity).order_by(Activity.created_at.desc())).all()
    out = []
    for a in rows:
        out.append({
            **a.to_summary(),
            "athlete_id": a.athlete_id,
            "athlete": a.athlete.name if a.athlete else None,
        })
    return out


@router.delete("/activities/{activity_id}")
def delete_activity(activity_id: str, db: Session = Depends(get_db)) -> dict:
    activity = db.get(Activity, activity_id)
    if not activity:
        raise HTTPException(status_code=404, detail="Тренировка не найдена")
    db.delete(activity)
    db.commit()
    return {"deleted": activity_id}


# --- Заявки на регистрацию ---

@router.get("/registrations")
def list_registrations(db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(
        select(RegistrationRequest).order_by(RegistrationRequest.created_at.desc())
    ).all()
    return [r.to_dict() for r in rows]


@router.post("/registrations/{req_id}/approve")
def approve_registration(req_id: str, db: Session = Depends(get_db)) -> dict:
    req = db.get(RegistrationRequest, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    athlete = create_athlete(db, req.name)
    req.status = "approved"
    req.athlete_id = athlete.id
    db.commit()
    return {"athlete_id": athlete.id, "name": athlete.name, "token": athlete.token}


@router.post("/registrations/{req_id}/reject")
def reject_registration(req_id: str, db: Session = Depends(get_db)) -> dict:
    req = db.get(RegistrationRequest, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    req.status = "rejected"
    db.commit()
    return {"ok": True}


@router.delete("/registrations/{req_id}")
def delete_registration(req_id: str, db: Session = Depends(get_db)) -> dict:
    req = db.get(RegistrationRequest, req_id)
    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")
    db.delete(req)
    db.commit()
    return {"deleted": req_id}

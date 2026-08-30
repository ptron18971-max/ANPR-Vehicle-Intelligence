from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db

app = FastAPI(title="Vehicle Intelligence Platform - Backend")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/health/db")
def health_check_db(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}


@app.get("/vehicles")
def get_vehicles(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT vehicle_id, plate_text, vehicle_type, vehicle_color, first_seen, last_seen
        FROM vehicles
        ORDER BY last_seen DESC
    """))
    rows = result.mappings().all()
    return [dict(row) for row in rows]
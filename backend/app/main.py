import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import text

from app.api import admin, auth, catalog, chats, garage, mapview, notifications, orders, payments, profile, ratings, reports, seller, ws
from app.database import engine
from app.realtime import hub
from app.schema_upgrade import ensure_schema
from app.services.storage import storage


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_schema()
    hub.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(
    title="autoparty API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(payments.router)
app.include_router(seller.router)
app.include_router(chats.router)
app.include_router(notifications.router)
app.include_router(ratings.router)
app.include_router(reports.router)
app.include_router(garage.router)
app.include_router(mapview.router)
app.include_router(admin.router)
app.include_router(ws.router)


@app.get("/api/health")
def health():
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "db": db_ok}


@app.get("/api/media/{filename}")
def media(filename: str):
    path = storage.resolve(filename)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return FileResponse(path)

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.database import engine, Base
from app.routers.usuarios.usuarios_router import router as usuarios_router
from app.routers.usuarios.auth_router import router as auth_router
from app.routers.usuarios.vehiculos_router import router as vehiculos_router
from app.routers.solicitudes.solicitudes_router import router as solicitudes_router
from app.routers.solicitudes.cotizaciones_router import router as cotizaciones_router
from app.routers.solicitudes.servicios_router import router as servicios_router
from app.routers.solicitudes.asignaciones_router import router as asignaciones_router
from app.routers.solicitudes.pagos_router import router as pagos_router
from app.routers.talleres.talleres_router import router as talleres_router
from app.routers.talleres.catalogo_servicio_router import router as catalogo_servicio_router
from app.routers.websockets_router import router as websockets_router
from app.seeds import run_seeds
import app.models

app = FastAPI()

UPLOADS_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")

WS_PROVIDER_LOG_FILE = Path(__file__).resolve().parent.parent / "ws_proveedor.log"
ws_provider_logger = logging.getLogger("ws_proveedor")
if not ws_provider_logger.handlers:
    ws_provider_logger.setLevel(logging.INFO)
    ws_provider_logger.propagate = False
    file_handler = logging.FileHandler(WS_PROVIDER_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    )
    ws_provider_logger.addHandler(file_handler)

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    run_seeds()

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(vehiculos_router)
app.include_router(solicitudes_router)
app.include_router(cotizaciones_router)
app.include_router(servicios_router)
app.include_router(asignaciones_router)
app.include_router(pagos_router)
app.include_router(talleres_router)
app.include_router(catalogo_servicio_router)
app.include_router(websockets_router)

@app.get("/")
def root():
    return {"message": "API funcionando"}

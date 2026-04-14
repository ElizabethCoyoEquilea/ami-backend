from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.routers.usuarios.usuarios_router import router as usuarios_router
from app.routers.usuarios.auth_router import router as auth_router
from app.routers.talleres.talleres_router import router as talleres_router
from app.seeds import run_seeds
import app.models

app = FastAPI()

origins = [
    "http://localhost:4200",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    run_seeds()

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(talleres_router)

@app.get("/")
def root():
    return {"message": "API funcionando"}

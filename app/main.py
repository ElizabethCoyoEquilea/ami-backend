from fastapi import FastAPI
from app.core.database import engine, Base
from app.routers.usuarios_router import router as usuarios_router
from app.routers.auth_router import router as auth_router
import app.models

app = FastAPI()

Base.metadata.create_all(bind=engine)

app.include_router(auth_router)
app.include_router(usuarios_router)

@app.get("/")
def root():
    return {"message": "API funcionando"}

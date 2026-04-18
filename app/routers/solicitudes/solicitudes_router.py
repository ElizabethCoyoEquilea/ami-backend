from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.solicitud_schema import SolicitudResponse
from app.services.solicitudes_service import registrar_solicitud


router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])


@router.post("", response_model=SolicitudResponse, status_code=status.HTTP_201_CREATED)
def crear_solicitud(
    id_vehiculo: int = Form(..., gt=0),
    descripcion: str = Form(..., min_length=1, max_length=500),
    latitud: float = Form(...),
    direccion: str | None = Form(default=None, max_length=255),
    longitud: float = Form(...),
    audio: UploadFile | None = File(default=None),
    imagenes: list[UploadFile] | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_solicitud(
        db=db,
        id_vehiculo=id_vehiculo,
        descripcion=descripcion,
        latitud=latitud,
        direccion=direccion,
        longitud=longitud,
        audio=audio,
        imagenes=imagenes,
    )

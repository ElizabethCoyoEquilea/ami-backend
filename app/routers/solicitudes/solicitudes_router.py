from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.solicitud_schema import (
    CancelarSolicitudRequest,
    CancelarSolicitudResponse,
    SolicitudResponse,
)
from app.services.solicitudes_service import (
    cancelar_solicitud,
    listar_mis_solicitudes,
    obtener_solicitud_por_id,
    registrar_solicitud,
)


router = APIRouter(prefix="/solicitudes", tags=["Solicitudes"])


@router.post("", response_model=SolicitudResponse, status_code=status.HTTP_201_CREATED)
async def crear_solicitud(
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
    return await registrar_solicitud(
        db=db,
        id_vehiculo=id_vehiculo,
        descripcion=descripcion,
        latitud=latitud,
        direccion=direccion,
        longitud=longitud,
        audio=audio,
        imagenes=imagenes,
    )


@router.post(
    "/cancelar_solicitud",
    response_model=CancelarSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
async def cancelar_solicitud_endpoint(
    data: CancelarSolicitudRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await cancelar_solicitud(db, data, current_user)


@router.get("/mis-solicitudes", response_model=list[SolicitudResponse], status_code=status.HTTP_200_OK)
def obtener_mis_solicitudes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_mis_solicitudes(db, current_user)


@router.get("/{id_solicitud}", response_model=SolicitudResponse, status_code=status.HTTP_200_OK)
def obtener_solicitud(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_solicitud_por_id(db, id_solicitud, current_user)

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.asignacion_schema import (
    AsignacionConSolicitudResponse,
    IniciarRecorridoRequest,
    IniciarRecorridoResponse,
)
from app.services.asignaciones_service import (
    iniciar_recorrido_asignacion,
    obtener_asignacion_por_id,
    obtener_asignacion_por_solicitud,
)


router = APIRouter(prefix="/asignaciones", tags=["Asignaciones"])


@router.post(
    "/iniciar_recorrido",
    response_model=IniciarRecorridoResponse,
    status_code=status.HTTP_200_OK,
)
async def iniciar_recorrido(
    data: IniciarRecorridoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await iniciar_recorrido_asignacion(db, data, current_user.id_usuario)


@router.get(
    "/solicitud/{id_solicitud}",
    response_model=AsignacionConSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_asignacion_solicitud(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_asignacion_por_solicitud(db, id_solicitud)


@router.get(
    "/{id_asignacion}",
    response_model=AsignacionConSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_asignacion_por_id(db, id_asignacion)

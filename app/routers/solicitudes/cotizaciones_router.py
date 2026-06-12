from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.cotizacion_schema import (
    InvitacionConSolicitudResponse,
    InvitacionRechazoAdministradorResponse,
    InvitacionResponse,
)
from app.services.cotizaciones_service import (
    listar_invitaciones_pendientes_taller,
    obtener_invitacion_por_id,
    registrar_invitacion_pendiente,
    rechazar_invitacion_por_solicitud,
)


router = APIRouter(prefix="/invitaciones", tags=["Invitaciones"])


@router.post(
    "/solicitud/{id_solicitud}/taller/{id_taller}",
    response_model=InvitacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_invitacion_pendiente(
    id_solicitud: int,
    id_taller: int,
    db: Session = Depends(get_db),
):
    return registrar_invitacion_pendiente(db, id_solicitud, id_taller)


@router.get(
    "/taller/{id_taller}/pendientes",
    response_model=list[InvitacionConSolicitudResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_invitaciones_pendientes_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_invitaciones_pendientes_taller(db, id_taller, current_user)


@router.get(
    "/{id_invitacion}",
    response_model=InvitacionConSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_invitacion(
    id_invitacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_invitacion_por_id(db, id_invitacion, current_user)


@router.patch(
    "/solicitud/{id_solicitud}/invitacion/{id_invitacion}/rechazar",
    response_model=InvitacionRechazoAdministradorResponse,
    status_code=status.HTTP_200_OK,
)
async def rechazar_invitacion_solicitud(
    id_solicitud: int,
    id_invitacion: int,
    db: Session = Depends(get_db),
):
    return await rechazar_invitacion_por_solicitud(db, id_solicitud, id_invitacion)

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.cotizacion_schema import (
    CotizacionConSolicitudResponse,
    CotizacionMontoEnviadoResponse,
    CotizacionRechazoAdministradorResponse,
    CotizacionResponse,
)
from app.services.cotizaciones_service import (
    enviar_monto_cotizacion_admin,
    listar_cotizaciones_pendientes_taller,
    obtener_cotizacion_por_id,
    registrar_cotizacion_pendiente,
    rechazar_cotizacion_por_solicitud,
)


router = APIRouter(prefix="/cotizaciones", tags=["Cotizaciones"])


@router.post(
    "/solicitud/{id_solicitud}/taller/{id_taller}",
    response_model=CotizacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_cotizacion_pendiente(
    id_solicitud: int,
    id_taller: int,
    db: Session = Depends(get_db),
):
    return registrar_cotizacion_pendiente(db, id_solicitud, id_taller)


@router.get(
    "/taller/{id_taller}/pendientes",
    response_model=list[CotizacionConSolicitudResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_cotizaciones_pendientes_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_cotizaciones_pendientes_taller(db, id_taller, current_user)


@router.get(
    "/{id_cotizacion}",
    response_model=CotizacionConSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_cotizacion(
    id_cotizacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_cotizacion_por_id(db, id_cotizacion, current_user)


@router.patch(
    "/solicitud/{id_solicitud}/cotizacion/{id_cotizacion}/rechazar",
    response_model=CotizacionRechazoAdministradorResponse,
    status_code=status.HTTP_200_OK,
)
async def rechazar_cotizacion_solicitud(
    id_solicitud: int,
    id_cotizacion: int,
    db: Session = Depends(get_db),
):
    return await rechazar_cotizacion_por_solicitud(db, id_solicitud, id_cotizacion)


@router.patch(
    "/solicitud/{id_solicitud}/cotizacion/{id_cotizacion}/vehiculo/{id_vehiculo}/monto",
    response_model=CotizacionMontoEnviadoResponse,
    status_code=status.HTTP_200_OK,
)
async def enviar_monto_cotizacion(
    id_solicitud: int,
    id_cotizacion: int,
    id_vehiculo: int,
    monto: Decimal = Query(..., ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await enviar_monto_cotizacion_admin(
        db,
        id_solicitud,
        id_cotizacion,
        id_vehiculo,
        monto,
        current_user,
    )

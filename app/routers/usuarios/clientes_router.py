from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.calificacion_cliente_schema import (
    CalificacionClienteResponse,
    ClienteReputacionResponse,
)
from app.services.calificaciones_cliente_service import (
    obtener_historial_calificaciones_cliente,
    obtener_promedio_y_total_cliente,
)

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get(
    "/{id_cliente}/calificaciones",
    response_model=list[CalificacionClienteResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_calificaciones_de_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_historial_calificaciones_cliente(db, id_cliente)


@router.get(
    "/{id_cliente}/reputacion",
    response_model=ClienteReputacionResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_reputacion_de_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_promedio_y_total_cliente(db, id_cliente)

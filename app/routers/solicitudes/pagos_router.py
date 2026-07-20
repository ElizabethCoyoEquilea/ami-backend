from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.pago_schema import PagoClienteResponse, PagoResponse, PagoUpdate
from app.services.pagos_service import listar_pagos_cliente, modificar_pago, obtener_pago


router = APIRouter(prefix="/pagos", tags=["Pagos"])


@router.get(
    "/cliente/mis-pagos",
    response_model=list[PagoClienteResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_mis_pagos_cliente(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_pagos_cliente(db, current_user.id_usuario)


@router.get("/{id_pago}", response_model=PagoResponse, status_code=status.HTTP_200_OK)
def obtener_pago_por_id(
    id_pago: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_pago(db, id_pago)


@router.patch("/{id_pago}", response_model=PagoResponse, status_code=status.HTTP_200_OK)
async def actualizar_pago(
    id_pago: int,
    pago_data: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await modificar_pago(db, id_pago, pago_data)

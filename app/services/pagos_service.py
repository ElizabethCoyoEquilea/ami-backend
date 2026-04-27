from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.pagos_repository import get_pago_by_id, update_pago
from app.schemas.solicitudes.pago_schema import PagoUpdate


def obtener_pago(db: Session, id_pago: int):
    pago = get_pago_by_id(db, id_pago)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    return pago


def modificar_pago(db: Session, id_pago: int, pago_data: PagoUpdate):
    pago = get_pago_by_id(db, id_pago)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    try:
        return update_pago(db, pago, pago_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el pago",
        )

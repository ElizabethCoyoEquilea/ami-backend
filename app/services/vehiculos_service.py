from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usuarios.cliente import Cliente
from app.models.usuarios.usuario import User
from app.repositories.usuarios_repository import get_cliente_by_user_id
from app.repositories.vehiculos_repository import (
    create_vehiculo,
    delete_vehiculo,
    get_vehiculo_by_id,
    get_vehiculo_by_placa,
    list_vehiculos_by_cliente,
    update_vehiculo,
)
from app.schemas.usuarios.vehiculo_schema import VehiculoCreate, VehiculoUpdate


def _get_cliente_actual(db: Session, current_user: User) -> Cliente:
    cliente = get_cliente_by_user_id(db, current_user.id_usuario)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario autenticado no tiene un registro de cliente",
        )
    return cliente


def _validar_placa_disponible(
    db: Session,
    placa: str,
    id_vehiculo_actual: int | None = None,
) -> None:
    vehiculo = get_vehiculo_by_placa(db, placa)
    if vehiculo and vehiculo.id_vehiculo != id_vehiculo_actual:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un vehiculo registrado con esa placa",
        )


def registrar_vehiculo(db: Session, vehiculo_data: VehiculoCreate, current_user: User):
    cliente = _get_cliente_actual(db, current_user)
    _validar_placa_disponible(db, vehiculo_data.placa)

    try:
        return create_vehiculo(db, vehiculo_data, cliente.id_cliente)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el vehiculo",
        )


def listar_mis_vehiculos(db: Session, current_user: User):
    cliente = _get_cliente_actual(db, current_user)
    return list_vehiculos_by_cliente(db, cliente.id_cliente)


def modificar_vehiculo(
    db: Session,
    id_vehiculo: int,
    vehiculo_data: VehiculoUpdate,
    current_user: User,
):
    cliente = _get_cliente_actual(db, current_user)
    vehiculo = get_vehiculo_by_id(db, id_vehiculo)
    if not vehiculo or vehiculo.id_cliente != cliente.id_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado",
        )

    if vehiculo_data.placa is not None:
        _validar_placa_disponible(db, vehiculo_data.placa, id_vehiculo)

    try:
        return update_vehiculo(db, vehiculo, vehiculo_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el vehiculo",
        )


def eliminar_vehiculo(db: Session, id_vehiculo: int, current_user: User) -> dict[str, str]:
    cliente = _get_cliente_actual(db, current_user)
    vehiculo = get_vehiculo_by_id(db, id_vehiculo)
    if not vehiculo or vehiculo.id_cliente != cliente.id_cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehiculo no encontrado",
        )

    try:
        delete_vehiculo(db, vehiculo)
        return {"message": "Vehiculo eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo eliminar el vehiculo",
        )

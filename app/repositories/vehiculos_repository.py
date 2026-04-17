from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.usuarios.vehiculo import Vehiculo
from app.schemas.usuarios.vehiculo_schema import VehiculoCreate, VehiculoUpdate


def create_vehiculo(db: Session, vehiculo_data: VehiculoCreate, id_cliente: int) -> Vehiculo:
    try:
        vehiculo = Vehiculo(**vehiculo_data.model_dump(), id_cliente=id_cliente)
        db.add(vehiculo)
        db.commit()
        db.refresh(vehiculo)
        return vehiculo
    except SQLAlchemyError:
        db.rollback()
        raise


def get_vehiculo_by_id(db: Session, id_vehiculo: int) -> Vehiculo | None:
    return db.query(Vehiculo).filter(Vehiculo.id_vehiculo == id_vehiculo).first()


def get_vehiculo_by_placa(db: Session, placa: str) -> Vehiculo | None:
    return db.query(Vehiculo).filter(Vehiculo.placa == placa).first()


def list_vehiculos_by_cliente(db: Session, id_cliente: int) -> list[Vehiculo]:
    return (
        db.query(Vehiculo)
        .filter(Vehiculo.id_cliente == id_cliente)
        .order_by(Vehiculo.id_vehiculo)
        .all()
    )


def update_vehiculo(
    db: Session,
    vehiculo: Vehiculo,
    vehiculo_data: VehiculoUpdate,
) -> Vehiculo:
    try:
        update_data = vehiculo_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(vehiculo, field, value)

        db.commit()
        db.refresh(vehiculo)
        return vehiculo
    except SQLAlchemyError:
        db.rollback()
        raise


def delete_vehiculo(db: Session, vehiculo: Vehiculo) -> None:
    try:
        db.delete(vehiculo)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise

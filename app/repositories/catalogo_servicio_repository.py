from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.talleres.catalogo_servicio import CatalogoServicio
from app.models.talleres.taller import Taller
from app.schemas.talleres.catalogo_servicio_schema import (
    CatalogoServicioCreate,
    CatalogoServicioUpdate,
)


def create_catalogo_servicio(
    db: Session,
    catalogo_data: CatalogoServicioCreate,
    estado: str = "activo",
) -> CatalogoServicio:
    try:
        catalogo_servicio = CatalogoServicio(
            **catalogo_data.model_dump(),
            estado=estado,
        )
        db.add(catalogo_servicio)
        db.commit()
        db.refresh(catalogo_servicio)
        return catalogo_servicio
    except SQLAlchemyError:
        db.rollback()
        raise


def get_catalogo_servicio_by_id(
    db: Session,
    id_catalogo_servicio: int,
) -> CatalogoServicio | None:
    return (
        db.query(CatalogoServicio)
        .filter(CatalogoServicio.id_catalogo_servicio == id_catalogo_servicio)
        .first()
    )


def get_active_catalogo_servicio_by_id(
    db: Session,
    id_catalogo_servicio: int,
) -> CatalogoServicio | None:
    return (
        db.query(CatalogoServicio)
        .filter(
            CatalogoServicio.id_catalogo_servicio == id_catalogo_servicio,
            CatalogoServicio.estado == "activo",
        )
        .first()
    )


def list_active_catalogo_servicios(db: Session) -> list[CatalogoServicio]:
    return (
        db.query(CatalogoServicio)
        .filter(CatalogoServicio.estado == "activo")
        .order_by(CatalogoServicio.id_catalogo_servicio)
        .all()
    )


def list_active_catalogo_servicios_by_usuario(
    db: Session,
    id_usuario: int,
) -> list[CatalogoServicio]:
    return (
        db.query(CatalogoServicio)
        .join(Taller, CatalogoServicio.id_taller == Taller.id_taller)
        .filter(
            Taller.id_usuario == id_usuario,
            Taller.activo.is_(True),
            CatalogoServicio.estado == "activo",
        )
        .order_by(CatalogoServicio.id_catalogo_servicio)
        .all()
    )


def list_active_catalogo_servicios_by_taller(
    db: Session,
    id_taller: int,
) -> list[CatalogoServicio]:
    return (
        db.query(CatalogoServicio)
        .filter(
            CatalogoServicio.id_taller == id_taller,
            CatalogoServicio.estado == "activo",
        )
        .order_by(CatalogoServicio.id_catalogo_servicio)
        .all()
    )


def list_catalogo_servicios_by_taller(
    db: Session,
    id_taller: int,
) -> list[CatalogoServicio]:
    return (
        db.query(CatalogoServicio)
        .filter(CatalogoServicio.id_taller == id_taller)
        .order_by(CatalogoServicio.estado)
        .all()
    )


def update_catalogo_servicio(
    db: Session,
    catalogo_servicio: CatalogoServicio,
    catalogo_data: CatalogoServicioUpdate,
) -> CatalogoServicio:
    try:
        update_data = catalogo_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(catalogo_servicio, field, value)

        db.commit()
        db.refresh(catalogo_servicio)
        return catalogo_servicio
    except SQLAlchemyError:
        db.rollback()
        raise


def logical_delete_catalogo_servicio(
    db: Session,
    catalogo_servicio: CatalogoServicio,
) -> CatalogoServicio:
    try:
        catalogo_servicio.estado = "inactivo"
        db.commit()
        db.refresh(catalogo_servicio)
        return catalogo_servicio
    except SQLAlchemyError:
        db.rollback()
        raise

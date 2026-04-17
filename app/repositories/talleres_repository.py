from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.talleres.taller import Taller
from app.models.usuarios.usuario_rol import UsuarioRol
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.schemas.talleres.taller_schema import TallerCreate, TallerUpdate


def create_taller(db: Session, taller_data: TallerCreate, id_usuario: int) -> Taller:
    try:
        taller = Taller(**taller_data.model_dump(), id_usuario=id_usuario)
        db.add(taller)
        db.flush()

        usuario_rol = UsuarioRol(
            id_usuario=id_usuario,
            id_rol=1,
            id_taller=taller.id_taller,
            activo=True,
        )
        db.add(usuario_rol)

        db.commit()
        db.refresh(taller)
        return taller
    except SQLAlchemyError:
        db.rollback()
        raise


def get_taller_by_id(db: Session, id_taller: int) -> Taller | None:
    return db.query(Taller).filter(Taller.id_taller == id_taller).first()


def get_active_taller_by_id(db: Session, id_taller: int) -> Taller | None:
    return (
        db.query(Taller)
        .filter(Taller.id_taller == id_taller, Taller.activo.is_(True))
        .first()
    )


def list_active_talleres(db: Session) -> list[Taller]:
    return db.query(Taller).filter(Taller.activo.is_(True)).order_by(Taller.id_taller).all()


def list_talleres_by_usuario(db: Session, id_usuario: int) -> list[Taller]:
    return (
        db.query(Taller)
        .filter(Taller.id_usuario == id_usuario)
        .order_by(Taller.id_taller)
        .all()
    )


def update_taller(db: Session, taller: Taller, taller_data: TallerUpdate) -> Taller:
    try:
        update_data = taller_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(taller, field, value)

        db.commit()
        db.refresh(taller)
        return taller
    except SQLAlchemyError:
        db.rollback()
        raise


def logical_delete_taller(db: Session, taller: Taller) -> Taller:
    try:
        taller.activo = False
        db.commit()
        db.refresh(taller)
        return taller
    except SQLAlchemyError:
        db.rollback()
        raise


def get_proveedores_by_taller(db: Session, id_taller: int) -> list[ProveedorServicio]:
    return (
        db.query(ProveedorServicio)
        .filter(ProveedorServicio.id_taller == id_taller)
        .all()
    )

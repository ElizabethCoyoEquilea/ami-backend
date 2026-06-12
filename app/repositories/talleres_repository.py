from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, joinedload, with_loader_criteria

from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.solicitudes.servicio import Servicio
from app.models.talleres.taller import Taller
from app.models.usuarios.usuario import User
from app.models.usuarios.usuario_rol import UsuarioRol
from app.models.usuarios.proveedor_especialidad import ProveedorEspecialidad
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.models.usuarios.vehiculo import Vehiculo
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
        .join(
            UsuarioRol,
            (UsuarioRol.id_usuario == ProveedorServicio.id_usuario)
            & (UsuarioRol.id_taller == ProveedorServicio.id_taller),
        )
        .options(
            joinedload(ProveedorServicio.usuario)
            .joinedload(User.persona),
            joinedload(ProveedorServicio.proveedor_especialidades)
            .joinedload(ProveedorEspecialidad.especialidad),
            with_loader_criteria(
                ProveedorEspecialidad,
                ProveedorEspecialidad.activo.is_(True),
                include_aliases=True,
            ),
        )
        .filter(
            ProveedorServicio.id_taller == id_taller,
            UsuarioRol.id_rol == 2,
            UsuarioRol.activo.is_(True),
        )
        .order_by(ProveedorServicio.id_proveedor)
        .all()
    )


def list_active_provider_assignments_by_user(
    db: Session, id_usuario: int
) -> list[ProveedorServicio]:
    return (
        db.query(ProveedorServicio)
        .join(
            UsuarioRol,
            (UsuarioRol.id_usuario == ProveedorServicio.id_usuario)
            & (UsuarioRol.id_taller == ProveedorServicio.id_taller),
        )
        .options(
            joinedload(ProveedorServicio.taller),
            joinedload(ProveedorServicio.usuario).joinedload(User.persona),
        )
        .filter(
            ProveedorServicio.id_usuario == id_usuario,
            UsuarioRol.id_rol == 2,
            UsuarioRol.activo.is_(True),
        )
        .order_by(ProveedorServicio.id_proveedor)
        .all()
    )


def get_active_provider_assignment_by_user_and_taller(
    db: Session,
    id_usuario: int,
    id_taller: int,
) -> ProveedorServicio | None:
    return (
        db.query(ProveedorServicio)
        .join(
            UsuarioRol,
            (UsuarioRol.id_usuario == ProveedorServicio.id_usuario)
            & (UsuarioRol.id_taller == ProveedorServicio.id_taller),
        )
        .options(
            joinedload(ProveedorServicio.usuario).joinedload(User.persona),
            joinedload(ProveedorServicio.taller),
        )
        .filter(
            ProveedorServicio.id_usuario == id_usuario,
            ProveedorServicio.id_taller == id_taller,
            UsuarioRol.id_rol == 2,
            UsuarioRol.activo.is_(True),
        )
        .first()
    )


def get_asignacion_with_solicitud_by_id(db: Session, id_asignacion: int) -> Asignacion | None:
    return (
        db.query(Asignacion)
        .options(
            joinedload(Asignacion.taller),
            joinedload(Asignacion.solicitud)
            .joinedload(Solicitud.vehiculo)
            .joinedload(Vehiculo.cliente)
        )
        .filter(Asignacion.id_asignacion == id_asignacion)
        .first()
    )


def list_asignaciones_by_taller(db: Session, id_taller: int) -> list[Asignacion]:
    return (
        db.query(Asignacion)
        .options(
            joinedload(Asignacion.solicitud),
            joinedload(Asignacion.servicios)
            .joinedload(Servicio.detalles_servicio)
            .joinedload(DetalleServicio.catalogo_servicio),
        )
        .filter(Asignacion.id_taller == id_taller)
        .order_by(Asignacion.id_asignacion)
        .all()
    )

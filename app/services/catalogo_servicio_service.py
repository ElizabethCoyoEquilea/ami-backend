from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.talleres.catalogo_servicio import CatalogoServicio
from app.repositories.catalogo_servicio_repository import (
    create_catalogo_servicio,
    get_active_catalogo_servicio_by_id,
    get_catalogo_servicio_by_id,
    list_active_catalogo_servicios_by_usuario,
    list_active_catalogo_servicios_by_taller,
    logical_delete_catalogo_servicio,
    update_catalogo_servicio,
)
from app.repositories.talleres_repository import get_active_taller_by_id
from app.schemas.talleres.catalogo_servicio_schema import (
    CatalogoServicioCreate,
    CatalogoServicioUpdate,
)


def _obtener_taller_del_usuario(db: Session, id_taller: int, id_usuario: int):
    taller = get_active_taller_by_id(db, id_taller)
    if not taller or taller.id_usuario != id_usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )
    return taller


def _validar_servicio_pertenece_usuario(
    db: Session,
    catalogo_servicio: CatalogoServicio,
    id_usuario: int,
) -> None:
    _obtener_taller_del_usuario(db, catalogo_servicio.id_taller, id_usuario)


def registrar_catalogo_servicio(
    db: Session,
    catalogo_data: CatalogoServicioCreate,
    id_usuario: int,
) -> CatalogoServicio:
    _obtener_taller_del_usuario(db, catalogo_data.id_taller, id_usuario)

    try:
        return create_catalogo_servicio(db, catalogo_data, estado="activo")
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo crear el servicio del catalogo",
        )


def listar_catalogo_servicios(db: Session, id_usuario: int) -> list[CatalogoServicio]:
    return list_active_catalogo_servicios_by_usuario(db, id_usuario)


def listar_catalogo_servicios_por_taller(
    db: Session,
    id_taller: int,
) -> list[CatalogoServicio]:
    taller = get_active_taller_by_id(db, id_taller)
    if not taller:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taller no encontrado",
        )
    return list_active_catalogo_servicios_by_taller(db, id_taller)


def obtener_catalogo_servicio(
    db: Session,
    id_catalogo_servicio: int,
    id_usuario: int,
) -> CatalogoServicio:
    catalogo_servicio = get_active_catalogo_servicio_by_id(db, id_catalogo_servicio)
    if not catalogo_servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio del catalogo no encontrado",
        )
    _validar_servicio_pertenece_usuario(db, catalogo_servicio, id_usuario)
    return catalogo_servicio


def modificar_catalogo_servicio(
    db: Session,
    id_catalogo_servicio: int,
    catalogo_data: CatalogoServicioUpdate,
    id_usuario: int,
) -> CatalogoServicio:
    catalogo_servicio = get_catalogo_servicio_by_id(db, id_catalogo_servicio)
    if not catalogo_servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio del catalogo no encontrado",
        )
    _validar_servicio_pertenece_usuario(db, catalogo_servicio, id_usuario)

    try:
        return update_catalogo_servicio(db, catalogo_servicio, catalogo_data)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el servicio del catalogo",
        )


def eliminar_catalogo_servicio(
    db: Session,
    id_catalogo_servicio: int,
    id_usuario: int,
) -> dict[str, str]:
    catalogo_servicio = get_active_catalogo_servicio_by_id(db, id_catalogo_servicio)
    if not catalogo_servicio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Servicio del catalogo no encontrado",
        )
    _validar_servicio_pertenece_usuario(db, catalogo_servicio, id_usuario)

    try:
        logical_delete_catalogo_servicio(db, catalogo_servicio)
        return {"message": "Servicio del catalogo eliminado correctamente"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo eliminar el servicio del catalogo",
        )

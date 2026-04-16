from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.talleres.catalogo_servicio_schema import (
    CatalogoServicioCreate,
    CatalogoServicioResponse,
    CatalogoServicioUpdate,
)
from app.schemas.usuarios.usuarios_schema import MessageResponse
from app.services.catalogo_servicio_service import (
    eliminar_catalogo_servicio,
    listar_catalogo_servicios,
    listar_catalogo_servicios_por_taller,
    modificar_catalogo_servicio,
    obtener_catalogo_servicio,
    registrar_catalogo_servicio,
)


router = APIRouter(prefix="/catalogo-servicios", tags=["Catalogo Servicios"])


@router.post("", response_model=CatalogoServicioResponse, status_code=status.HTTP_201_CREATED)
def crear_catalogo_servicio(
    catalogo_data: CatalogoServicioCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return registrar_catalogo_servicio(db, catalogo_data, current_user.id_usuario)


@router.get("", response_model=list[CatalogoServicioResponse], status_code=status.HTTP_200_OK)
def obtener_catalogo_servicios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_catalogo_servicios(db, current_user.id_usuario)


@router.get(
    "/taller/{id_taller}",
    response_model=list[CatalogoServicioResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_catalogo_servicios_por_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_catalogo_servicios_por_taller(db, id_taller, current_user.id_usuario)


@router.get(
    "/{id_catalogo_servicio}",
    response_model=CatalogoServicioResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_catalogo_servicio_por_id(
    id_catalogo_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_catalogo_servicio(db, id_catalogo_servicio, current_user.id_usuario)


@router.put(
    "/{id_catalogo_servicio}",
    response_model=CatalogoServicioResponse,
    status_code=status.HTTP_200_OK,
)
def actualizar_catalogo_servicio(
    id_catalogo_servicio: int,
    catalogo_data: CatalogoServicioUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return modificar_catalogo_servicio(
        db,
        id_catalogo_servicio,
        catalogo_data,
        current_user.id_usuario,
    )


@router.delete(
    "/{id_catalogo_servicio}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
def borrar_catalogo_servicio(
    id_catalogo_servicio: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return eliminar_catalogo_servicio(db, id_catalogo_servicio, current_user.id_usuario)

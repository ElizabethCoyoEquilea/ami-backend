from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.solicitudes.asignacion import Asignacion
from app.models.usuarios.usuario import User
from app.repositories.asignaciones_repository import get_asignacion_detalle_by_id


def obtener_asignacion_por_id(
    db: Session,
    id_asignacion: int,
    current_user: User,
) -> Asignacion:
    asignacion = get_asignacion_detalle_by_id(db, id_asignacion)
    if not asignacion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada",
        )

    es_admin_taller = bool(
        asignacion.taller and asignacion.taller.id_usuario == current_user.id_usuario
    )
    es_proveedor_asignado = bool(
        asignacion.proveedor_servicio
        and asignacion.proveedor_servicio.id_usuario == current_user.id_usuario
    )
    cliente = (
        asignacion.solicitud.vehiculo.cliente
        if asignacion.solicitud and asignacion.solicitud.vehiculo
        else None
    )
    es_cliente_dueno = bool(cliente and cliente.id_usuario == current_user.id_usuario)

    if not es_admin_taller and not es_proveedor_asignado and not es_cliente_dueno:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asignacion no encontrada para el usuario autenticado",
        )

    return asignacion

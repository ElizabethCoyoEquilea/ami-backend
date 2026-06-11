import logging

from sqlalchemy.orm import Session

from app.repositories.talleres_repository import get_active_taller_by_id, get_proveedores_by_taller
from app.websockets.connection_manager import providers_ws_manager


logger = logging.getLogger("notificaciones")


async def notificar_nueva_solicitud_a_talleres(db: Session, invitaciones) -> None:
    payload = {"tipo": "nueva solicitud"}
    await _notificar_talleres_por_invitaciones(db, invitaciones, payload)


async def notificar_invitacion_expirada_a_talleres(db: Session, invitaciones) -> None:
    payload = {"tipo": "invitacion_expirada"}
    await _notificar_talleres_por_invitaciones(db, invitaciones, payload)


async def _notificar_talleres_por_invitaciones(db: Session, invitaciones, payload: dict) -> None:
    taller_ids = sorted({invitacion.id_taller for invitacion in invitaciones})

    for id_taller in taller_ids:
        taller = get_active_taller_by_id(db, id_taller)
        if not taller:
            continue

        usuarios_notificados = {taller.id_usuario}
        for proveedor in get_proveedores_by_taller(db, id_taller):
            if (proveedor.estado or "").lower() != "disponible":
                continue
            usuarios_notificados.add(proveedor.id_usuario)

        for id_usuario in usuarios_notificados:
            enviado = await providers_ws_manager.send_to_user(id_usuario, payload)
            logger.info(
                "notificacion_taller_ws tipo=%s user=%s id_taller=%s enviado=%s",
                payload.get("tipo"),
                id_usuario,
                id_taller,
                enviado,
            )

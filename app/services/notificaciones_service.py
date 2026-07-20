import logging

from sqlalchemy.orm import Session

from app.repositories.talleres_repository import get_active_taller_by_id, get_proveedores_by_taller
from app.websockets.connection_manager import clients_ws_manager, providers_ws_manager


logger = logging.getLogger("notificaciones")


async def notificar_nueva_solicitud_a_talleres(db: Session, invitaciones) -> None:
    payload = {"tipo": "nueva solicitud"}
    await _notificar_talleres_por_invitaciones(db, invitaciones, payload)


async def notificar_solicitud_cancelada_a_talleres(db: Session, invitaciones) -> None:
    invitaciones = list(invitaciones)
    id_solicitud = invitaciones[0].id_solicitud if invitaciones else None
    payload = {
        "tipo": "solcitud_cancelada",
        "data": {
            "id_solicitud": id_solicitud,
            "id_invitaciones": [
                invitacion.id_invitacion for invitacion in invitaciones
            ],
        },
    }
    await _notificar_talleres_por_invitaciones(db, invitaciones, payload)


async def notificar_invitacion_expirada_a_talleres(db: Session, invitaciones) -> None:
    payload = {"tipo": "invitacion_expirada"}
    await _notificar_talleres_por_invitaciones(db, invitaciones, payload)


async def notificar_solicitud_expirada_a_cliente(solicitud) -> dict | None:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_solicitud_expirada_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return None

    payload = {
        "tipo": "solicitud_expirada",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return payload


async def notificar_solicitud_asignada_a_cliente(solicitud) -> dict | None:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_solicitud_asignada_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return None

    payload = {
        "tipo": "solicitud_asignada",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return payload


async def notificar_en_camino_a_cliente(solicitud) -> bool:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_en_camino_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return False

    payload = {
        "tipo": "en_camino",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return enviado


async def notificar_seguimiento_iniciado_a_admin_taller(asignacion, solicitud) -> list[bool]:
    taller = asignacion.taller
    if not taller:
        logger.warning(
            "notificacion_seguimiento_iniciado_sin_taller id_asignacion=%s",
            asignacion.id_asignacion,
        )
        return [False, False]

    seguimiento_payload = {
        "tipo": "seguimiento_iniciado",
        "data": {
            "id_asignacion": asignacion.id_asignacion,
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    recorrido_payload = {
        "tipo": "proveedor_recorrido",
        "data": {
            "id_asignacion": asignacion.id_asignacion,
            "id_solicitud": solicitud.id_solicitud,
            "latitud": taller.latitud,
            "longitud": taller.longitud,
        },
    }

    seguimiento_enviado = await providers_ws_manager.send_to_user(
        taller.id_usuario,
        seguimiento_payload,
    )
    recorrido_enviado = await providers_ws_manager.send_to_user(
        taller.id_usuario,
        recorrido_payload,
    )
    logger.info(
        "notificacion_admin_taller_ws user_destino=%s id_taller=%s id_asignacion=%s seguimiento=%s recorrido=%s payload_recorrido=%s",
        taller.id_usuario,
        taller.id_taller,
        asignacion.id_asignacion,
        seguimiento_enviado,
        recorrido_enviado,
        recorrido_payload,
    )
    return [seguimiento_enviado, recorrido_enviado]


async def notificar_proveedor_llego_a_cliente(solicitud) -> bool:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_proveedor_llego_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return False

    payload = {
        "tipo": "proovedor_llego",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return enviado


async def notificar_solicitud_aceptada_a_proveedores_taller(
    db: Session,
    id_taller: int,
    payload: dict,
) -> list[int]:
    usuarios_notificados: list[int] = []
    for proveedor in get_proveedores_by_taller(db, id_taller):
        enviado = await providers_ws_manager.send_to_user(
            proveedor.id_usuario,
            payload,
        )
        logger.info(
            "notificacion_proveedor_ws tipo=%s user=%s id_taller=%s enviado=%s",
            payload.get("tipo"),
            proveedor.id_usuario,
            id_taller,
            enviado,
        )
        if enviado:
            usuarios_notificados.append(proveedor.id_usuario)

    return usuarios_notificados


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


async def notificar_pendiente_pago_a_cliente(solicitud) -> bool:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_pendiente_pago_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return False

    payload = {
        "tipo": "pendiente_pago",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return enviado


async def notificar_servicio_finalizado_a_cliente(solicitud) -> bool:
    cliente = solicitud.vehiculo.cliente if solicitud.vehiculo else None
    if not cliente:
        logger.warning(
            "notificacion_finalizado_sin_cliente id_solicitud=%s",
            solicitud.id_solicitud,
        )
        return False

    payload = {
        "tipo": "servicio_finalizado",
        "data": {
            "id_solicitud": solicitud.id_solicitud,
        },
    }
    enviado = await clients_ws_manager.send_to_user(cliente.id_usuario, payload)
    logger.info(
        "notificacion_cliente_ws tipo=%s user=%s id_solicitud=%s enviado=%s",
        payload["tipo"],
        cliente.id_usuario,
        solicitud.id_solicitud,
        enviado,
    )
    return enviado


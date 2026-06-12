import asyncio
import logging

from app.core.database import SessionLocal
from app.repositories.solicitudes_repository import get_solicitud_by_id
from app.services.cotizaciones_service import (
    listar_solicitud_ids_con_invitaciones_vencidas,
    refresh_invitaciones_y_generar_siguiente_ronda,
)
from app.services.notificaciones_service import (
    notificar_invitacion_expirada_a_talleres,
    notificar_nueva_solicitud_a_talleres,
    notificar_solicitud_expirada_a_cliente,
)


logger = logging.getLogger("invitaciones_scheduler")


async def procesar_invitaciones_vencidas() -> dict[str, int]:
    db = SessionLocal()
    try:
        solicitud_ids = listar_solicitud_ids_con_invitaciones_vencidas(db)
        total_invitaciones_expiradas = 0
        total_nuevas_invitaciones = 0

        for id_solicitud in solicitud_ids:
            solicitud = get_solicitud_by_id(db, id_solicitud)
            if not solicitud:
                continue

            estado_anterior = solicitud.estado
            invitaciones_expiradas, nuevas_invitaciones = refresh_invitaciones_y_generar_siguiente_ronda(
                db,
                solicitud,
                incluir_expiradas=True,
            )
            total_invitaciones_expiradas += len(invitaciones_expiradas)
            total_nuevas_invitaciones += len(nuevas_invitaciones)
            await notificar_invitacion_expirada_a_talleres(db, invitaciones_expiradas)
            await notificar_nueva_solicitud_a_talleres(db, nuevas_invitaciones)
            if estado_anterior != "sin_cobertura" and solicitud.estado == "sin_cobertura":
                await notificar_solicitud_expirada_a_cliente(solicitud)

        if solicitud_ids:
            logger.info(
                "invitaciones_vencidas_procesadas solicitudes=%s invitaciones_expiradas=%s nuevas_invitaciones=%s",
                len(solicitud_ids),
                total_invitaciones_expiradas,
                total_nuevas_invitaciones,
            )

        return {
            "solicitudes_procesadas": len(solicitud_ids),
            "invitaciones_expiradas": total_invitaciones_expiradas,
            "nuevas_invitaciones": total_nuevas_invitaciones,
        }
    finally:
        db.close()


async def ejecutar_scheduler_invitaciones(intervalo_segundos: int = 30) -> None:
    logger.info("scheduler_invitaciones_iniciado intervalo_segundos=%s", intervalo_segundos)

    while True:
        try:
            await procesar_invitaciones_vencidas()
        except asyncio.CancelledError:
            logger.info("scheduler_invitaciones_cancelado")
            raise
        except Exception:
            logger.exception("scheduler_invitaciones_error")

        await asyncio.sleep(intervalo_segundos)

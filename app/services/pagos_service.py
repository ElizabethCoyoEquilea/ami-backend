from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.repositories.pagos_repository import (
    get_pago_by_id,
    list_pagos_pagados_by_cliente_usuario,
    update_pago,
)
from app.schemas.solicitudes.pago_schema import PagoUpdate


def obtener_pago(db: Session, id_pago: int):
    pago = get_pago_by_id(db, id_pago)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    return pago


def listar_pagos_cliente(db: Session, id_usuario: int) -> list[dict]:
    pagos = list_pagos_pagados_by_cliente_usuario(db, id_usuario)
    response = []

    for pago in pagos:
        servicio = pago.servicio
        asignacion = servicio.asignacion if servicio else None
        solicitud = asignacion.solicitud if asignacion else None
        vehiculo = solicitud.vehiculo if solicitud else None

        if not servicio or not asignacion or not solicitud or not vehiculo:
            continue

        response.append(
            {
                "pago": {
                    "id_pago": pago.id_pago,
                    "monto": float(pago.monto),
                    "estado": pago.estado,
                    "metodo": pago.metodo,
                    "fecha": pago.fecha,
                },
                "servicio": {
                    "id_servicio": servicio.id_servicio,
                    "total": float(servicio.total or 0),
                    "fecha_inicio": servicio.fecha_inicio,
                    "fecha_fin": servicio.fecha_fin,
                    "estado": servicio.estado,
                    "detalles_servicio": [
                        {
                            "id_detalle_servicio": detalle.id_detalle_servicio,
                            "id_catalogo_servicio": detalle.id_catalogo_servicio,
                            "nombre": detalle.nombre,
                            "cantidad": detalle.cantidad,
                            "precio": float(detalle.precio),
                            "sub_total": float(detalle.sub_total),
                            "observacion": detalle.observacion,
                        }
                        for detalle in servicio.detalles_servicio
                    ],
                },
                "asignacion": {
                    "id_asignacion": asignacion.id_asignacion,
                    "id_taller": asignacion.id_taller,
                    "id_proveedor": asignacion.id_proveedor,
                    "fecha_inicio": asignacion.fecha_inicio,
                    "fecha_fin": asignacion.fecha_fin,
                    "tiempo_llegada": asignacion.tiempo_llegada,
                    "estado": asignacion.estado,
                },
                "solicitud": {
                    "id_solicitud": solicitud.id_solicitud,
                    "descripcion": solicitud.descripcion,
                    "fecha": solicitud.fecha,
                    "estado": solicitud.estado,
                },
                "vehiculo": {
                    "id_vehiculo": vehiculo.id_vehiculo,
                    "marca": vehiculo.marca,
                    "modelo": vehiculo.modelo,
                    "placa": vehiculo.placa,
                },
            }
        )

    return response


async def modificar_pago(db: Session, id_pago: int, pago_data: PagoUpdate):
    pago = get_pago_by_id(db, id_pago)
    if not pago:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pago no encontrado",
        )

    try:
        pago_actualizado = update_pago(db, pago, pago_data)
        
        # Notify client that the service is completed/paid
        if (pago_actualizado and 
            pago_actualizado.servicio and 
            pago_actualizado.servicio.asignacion and 
            pago_actualizado.servicio.asignacion.solicitud):
            from app.services.notificaciones_service import notificar_servicio_finalizado_a_cliente
            await notificar_servicio_finalizado_a_cliente(pago_actualizado.servicio.asignacion.solicitud)

        return pago_actualizado
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo actualizar el pago",
        )

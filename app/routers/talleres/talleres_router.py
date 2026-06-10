import asyncio
import logging
from datetime import date, time

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.encoders import jsonable_encoder
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user, verify_token
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.asignacion_schema import AsignacionConSolicitudResponse
from app.schemas.talleres.taller_schema import (
    ListarProveedoresResponse,
    ProveedorServicioEspecialidadesUpdate,
    ProveedorServicioResponse,
    TallerCreate,
    TallerDashboardHoyResponse,
    TallerReporteFinancieroResponse,
    TallerReporteOperativoResponse,
    TallerRecomendadoResponse,
    TallerResponse,
    TallerUpdate,
)
from app.repositories.solicitudes_repository import get_solicitud_by_id
from app.schemas.usuarios.usuarios_schema import MessageResponse
from app.services.talleres_service import (
    eliminar_taller,
    listar_talleres_por_usuario,
    listar_talleres,
    modificar_taller,
    obtener_dashboard_taller_hoy,
    obtener_reporte_financiero_taller,
    obtener_reporte_operativo_taller,
    obtener_taller,
    registrar_taller,
    listar_proveedores_taller,
    listar_asignaciones_taller,
    actualizar_especialidades_proveedor_servicio,
)
from app.services.workshop_recommendation_service import recommend_workshops


router = APIRouter(prefix="/talleres", tags=["Talleres"])
logger = logging.getLogger("talleres")


@router.post("", response_model=TallerResponse, status_code=status.HTTP_201_CREATED)
def crear_taller(
    nombre: str = Form(..., min_length=1, max_length=150),
    descripcion: str | None = Form(default=None, max_length=500),
    radio_cobertura: float = Form(..., ge=0, le=100),
    calificacion: float = Form(default=0, ge=0, le=5),
    direccion: str = Form(..., min_length=1, max_length=255),
    longitud: float | None = Form(default=None),
    latitud: float | None = Form(default=None),
    horario_inicio: time = Form(...),
    horario_fin: time = Form(...),
    estado: str | None = Form(default=None),
    activo: bool = Form(default=True),
    qr: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    taller_data = TallerCreate(
        nombre=nombre,
        descripcion=descripcion,
        radio_cobertura=radio_cobertura,
        calificacion=calificacion,
        direccion=direccion,
        longitud=longitud,
        latitud=latitud,
        horario_inicio=horario_inicio,
        horario_fin=horario_fin,
        estado=estado,
        activo=activo,
    )
    return registrar_taller(db, taller_data, current_user.id_usuario, qr)


@router.get("", response_model=list[TallerResponse], status_code=status.HTTP_200_OK)
def obtener_talleres(db: Session = Depends(get_db)):
    return listar_talleres(db)


@router.get("/mis-talleres", response_model=list[TallerResponse], status_code=status.HTTP_200_OK)
def obtener_mis_talleres(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_talleres_por_usuario(db, current_user.id_usuario)


@router.get(
    "/recomendados",
    response_model=list[TallerRecomendadoResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_talleres_recomendados(
    id_solicitud: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    solicitud = get_solicitud_by_id(db, id_solicitud)
    if not solicitud:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitud no encontrada",
        )

    if solicitud.latitud is None or solicitud.longitud is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La solicitud no tiene latitud o longitud",
        )

    return recommend_workshops(
        db=db,
        client_lat=solicitud.latitud,
        client_lng=solicitud.longitud,
    )


@router.get(
    "/{id_taller}/dashboard/hoy",
    response_model=TallerDashboardHoyResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_dashboard_hoy_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_dashboard_taller_hoy(db, id_taller, current_user.id_usuario)


@router.get(
    "/{id_taller}/reportes/operativo",
    response_model=TallerReporteOperativoResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_reporte_operativo(
    id_taller: int,
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_reporte_operativo_taller(
        db=db,
        id_taller=id_taller,
        id_usuario=current_user.id_usuario,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )


@router.get(
    "/{id_taller}/reportes/financiero",
    response_model=TallerReporteFinancieroResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_reporte_financiero(
    id_taller: int,
    fecha_inicio: date,
    fecha_fin: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_reporte_financiero_taller(
        db=db,
        id_taller=id_taller,
        id_usuario=current_user.id_usuario,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )


@router.get("/{id_taller}", response_model=TallerResponse, status_code=status.HTTP_200_OK)
def obtener_taller_por_id(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_taller(db, id_taller)


@router.get("/{id_taller}/detalle", response_model=TallerResponse, status_code=status.HTTP_200_OK)
def obtener_detalle_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_taller(db, id_taller)


@router.put("/{id_taller}", response_model=TallerResponse, status_code=status.HTTP_200_OK)
def actualizar_taller(
    id_taller: int,
    nombre: str | None = Form(default=None, min_length=1, max_length=150),
    descripcion: str | None = Form(default=None, max_length=500),
    radio_cobertura: float | None = Form(default=None, ge=0, le=100),
    calificacion: float | None = Form(default=None, ge=0, le=5),
    direccion: str | None = Form(default=None, min_length=1, max_length=255),
    longitud: float | None = Form(default=None),
    latitud: float | None = Form(default=None),
    horario_inicio: time | None = Form(default=None),
    horario_fin: time | None = Form(default=None),
    estado: str | None = Form(default=None),
    activo: bool | None = Form(default=None),
    qr: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = {
        "nombre": nombre,
        "descripcion": descripcion,
        "radio_cobertura": radio_cobertura,
        "calificacion": calificacion,
        "direccion": direccion,
        "longitud": longitud,
        "latitud": latitud,
        "horario_inicio": horario_inicio,
        "horario_fin": horario_fin,
        "estado": estado,
        "activo": activo,
    }
    taller_data = TallerUpdate(
        **{field: value for field, value in update_data.items() if value is not None}
    )
    return modificar_taller(db, id_taller, taller_data, current_user.id_usuario, qr)


@router.delete("/{id_taller}", response_model=MessageResponse, status_code=status.HTTP_200_OK)
def borrar_taller(id_taller: int, db: Session = Depends(get_db)):
    return eliminar_taller(db, id_taller)


@router.get("/{id_taller}/proveedores", response_model=ListarProveedoresResponse, status_code=status.HTTP_200_OK)
def obtener_proveedores_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lista los proveedores de servicio asignados a un taller específico.
    
    Requiere: Authorization: Bearer <token>
    """
    return listar_proveedores_taller(db, id_taller, current_user.id_usuario)


@router.put(
    "/{id_taller}/proveedor-servicio",
    response_model=ProveedorServicioResponse,
    status_code=status.HTTP_200_OK,
)
def editar_proveedor_servicio(
    id_taller: int,
    proveedor_data: ProveedorServicioEspecialidadesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return actualizar_especialidades_proveedor_servicio(
        db,
        id_taller,
        proveedor_data,
        current_user.id_usuario,
    )


@router.get(
    "/{id_taller}/asignaciones",
    response_model=list[AsignacionConSolicitudResponse],
    status_code=status.HTTP_200_OK,
)
def obtener_asignaciones_taller(
    id_taller: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return listar_asignaciones_taller(db, id_taller)


@router.websocket("/{id_taller}/dashboard/ws")
async def websocket_dashboard_taller(
    websocket: WebSocket,
    id_taller: int,
    token: str,
    intervalo_segundos: int = 5,
):
    db = SessionLocal()
    id_usuario: int | None = None
    intervalo = max(2, min(intervalo_segundos, 60))

    try:
        payload = verify_token(token)
        id_usuario = int(payload.get("sub"))
        usuario = db.query(User).filter(User.id_usuario == id_usuario, User.activo.is_(True)).first()
        if not usuario:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        logger.info("dashboard_ws_open user=%s id_taller=%s intervalo=%s", id_usuario, id_taller, intervalo)

        while True:
            resumen = obtener_dashboard_taller_hoy(db, id_taller, id_usuario)
            await websocket.send_json(
                jsonable_encoder({
                    "tipo": "dashboard_taller_actualizado",
                    "data": resumen,
                })
            )
            await asyncio.sleep(intervalo)
    except (HTTPException, JWTError, TypeError, ValueError):
        logger.exception("dashboard_ws_closed_by_error user=%s id_taller=%s", id_usuario, id_taller)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
    except WebSocketDisconnect:
        logger.info("dashboard_ws_closed user=%s id_taller=%s", id_usuario, id_taller)
    finally:
        db.close()

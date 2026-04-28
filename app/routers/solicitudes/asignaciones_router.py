from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.solicitudes.asignacion_schema import AsignacionConSolicitudResponse
from app.services.asignaciones_service import obtener_asignacion_por_id


router = APIRouter(prefix="/asignaciones", tags=["Asignaciones"])


@router.get(
    "/{id_asignacion}",
    response_model=AsignacionConSolicitudResponse,
    status_code=status.HTTP_200_OK,
)
def obtener_asignacion(
    id_asignacion: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return obtener_asignacion_por_id(db, id_asignacion)

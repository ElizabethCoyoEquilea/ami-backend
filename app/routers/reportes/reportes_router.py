from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.usuarios.usuario import User
from app.schemas.reportes_schema import ReporteAIRequest, ReporteAIResponse
from app.services.reportes_ai_service import generar_reporte_ai


router = APIRouter(prefix="/reportes", tags=["Reportes"])


@router.post("/ia", response_model=ReporteAIResponse, status_code=status.HTTP_200_OK)
def generar_reporte_con_ia(
    request: ReporteAIRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return generar_reporte_ai(db, request, current_user.id_usuario)

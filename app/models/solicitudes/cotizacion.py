from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Invitacion(Base):
    __tablename__ = "invitacion"

    id_invitacion = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    numero_ronda = Column(Integer, nullable=False, default=1, server_default="1")
    estado = Column(String(30), nullable=False, default="pendiente", server_default="pendiente")
    fecha_hora_envio = Column(DateTime, nullable=False, server_default=func.now())
    fecha_hora_expiracion = Column(DateTime, nullable=True)
    fecha_hora_respuesta = Column(DateTime, nullable=True)

    solicitud = relationship("Solicitud", back_populates="invitaciones")
    taller = relationship("Taller", back_populates="invitaciones")

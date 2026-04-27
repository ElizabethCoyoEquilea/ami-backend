from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Calificacion(Base):
    __tablename__ = "calificacion"

    id_calificacion = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_servicio = Column(Integer, ForeignKey("servicio.id_servicio"), nullable=False, unique=True, index=True)
    puntuacion = Column(Integer, nullable=False)
    comentario = Column(String(500), nullable=True)
    fecha = Column(DateTime, nullable=False, server_default=func.now())

    servicio = relationship("Servicio", back_populates="calificacion")

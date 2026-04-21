from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Asignacion(Base):
    __tablename__ = "asignacion"

    id_asignacion = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_catalogo_servicio = Column(Integer, ForeignKey("catalogo_servicio.id_catalogo_servicio"), nullable=True, index=True)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    estado = Column(String(30), nullable=False, default="pendiente")

    solicitud = relationship("Solicitud", back_populates="asignaciones")
    taller = relationship("Taller", back_populates="asignaciones")
    catalogo_servicio = relationship("CatalogoServicio", back_populates="asignaciones")

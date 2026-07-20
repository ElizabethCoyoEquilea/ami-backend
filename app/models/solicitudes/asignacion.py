from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Asignacion(Base):
    __tablename__ = "asignacion"

    id_asignacion = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_proveedor = Column(Integer, ForeignKey("proveedor_servicio.id_proveedor"), nullable=True, index=True)
    fecha_inicio = Column(DateTime, nullable=False, server_default=func.now())
    fecha_fin = Column(DateTime, nullable=True)
    tiempo_llegada = Column(Numeric(10, 2), nullable=True)
    estado = Column(String(30), nullable=False, default="pendiente")

    solicitud = relationship("Solicitud", back_populates="asignaciones")
    taller = relationship("Taller", back_populates="asignaciones")
    proveedor_servicio = relationship("ProveedorServicio", back_populates="asignaciones")
    servicios = relationship("Servicio", back_populates="asignacion", cascade="all, delete-orphan")

    @property
    def estado_servicio(self) -> str | None:
        if self.servicios:
            latest = sorted(self.servicios, key=lambda s: s.id_servicio, reverse=True)[0]
            return latest.estado
        return None


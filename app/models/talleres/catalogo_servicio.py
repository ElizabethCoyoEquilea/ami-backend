from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class CatalogoServicio(Base):
    __tablename__ = "catalogo_servicio"

    id_catalogo_servicio = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    id_especialidad = Column(Integer, ForeignKey("especialidad.id_especialidad"), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)
    precio_estandar = Column(Float, nullable=False)
    estado = Column(String(20), nullable=False, default="activo")
    fecha_creacion = Column(DateTime, nullable=False, server_default=func.now())

    taller = relationship("Taller", back_populates="catalogo_servicios")
    especialidad = relationship("Especialidad", back_populates="catalogo_servicios")
    detalles_servicio = relationship("DetalleServicio", back_populates="catalogo_servicio", cascade="all, delete-orphan")

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Solicitud(Base):
    __tablename__ = "solicitud"

    id_solicitud = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_vehiculo = Column(Integer, ForeignKey("vehiculo.id_vehiculo"), nullable=False, index=True)
    id_zona = Column(Integer, ForeignKey("zona.id_zona"), nullable=True, index=True)
    descripcion = Column(String(500), nullable=False)
    latitud = Column(Float, nullable=True)
    direccion = Column(String(255), nullable=True)
    longitud = Column(Float, nullable=True)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    prioridad = Column(String(20), nullable=True)
    observaciones = Column(String(500), nullable=True)
    recomendacion = Column(Text, nullable=True)
    audio = Column(String(1000), nullable=True)
    imagenes = Column(JSON, nullable=True)
    ronda_actual = Column(Integer, nullable=False, default=1, server_default="1")
    estado = Column(String(30), nullable=False, default="pendiente")

    vehiculo = relationship("Vehiculo", back_populates="solicitudes")
    zona = relationship("Zona", back_populates="solicitudes")
    invitaciones = relationship("Invitacion", back_populates="solicitud", cascade="all, delete-orphan")
    asignaciones = relationship("Asignacion", back_populates="solicitud", cascade="all, delete-orphan")

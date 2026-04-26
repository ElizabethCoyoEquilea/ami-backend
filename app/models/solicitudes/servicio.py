from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Servicio(Base):
    __tablename__ = "servicio"

    id_servicio = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=False, index=True)
    id_pago = Column(Integer, ForeignKey("pago.id_pago"), nullable=True, unique=True, index=True)
    total = Column(Numeric(12, 2), nullable=True, default=0)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(30), nullable=False, default="En curso")

    asignacion = relationship("Asignacion", back_populates="servicios")
    pago = relationship("Pago", back_populates="servicio", uselist=False)
    detalles_servicio = relationship("DetalleServicio", back_populates="servicio", cascade="all, delete-orphan")

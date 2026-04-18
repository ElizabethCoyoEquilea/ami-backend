from sqlalchemy import Column, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.core.database import Base


class Cotizacion(Base):
    __tablename__ = "cotizacion"

    id_cotizacion = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_solicitud = Column(Integer, ForeignKey("solicitud.id_solicitud"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    monto = Column(Numeric(12, 2), nullable=False)

    solicitud = relationship("Solicitud", back_populates="cotizaciones")
    taller = relationship("Taller", back_populates="cotizaciones")

from sqlalchemy import Column, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Pago(Base):
    __tablename__ = "pago"

    id_pago = Column(Integer, primary_key=True, autoincrement=True, index=True)
    monto = Column(Numeric(12, 2), nullable=False)
    estado = Column(String(30), nullable=False, default="pendiente")
    metodo = Column(String(50), nullable=False)
    fecha = Column(DateTime, nullable=False, server_default=func.now())

    servicio = relationship("Servicio", back_populates="pago", uselist=False)

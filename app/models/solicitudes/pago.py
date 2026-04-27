from sqlalchemy import Column, DateTime, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Pago(Base):
    __tablename__ = "pago"

    id_pago = Column(Integer, primary_key=True, autoincrement=True, index=True)
    monto = Column(Numeric(12, 2), nullable=False)
    estado = Column(String(30), nullable=False, default="pendiente")
    metodo = Column(String(50), nullable=True)
    fecha = Column(DateTime, nullable=True)

    servicio = relationship("Servicio", back_populates="pago", uselist=False)

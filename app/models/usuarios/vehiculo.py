from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculo"

    id_vehiculo = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_cliente = Column(Integer, ForeignKey("cliente.id_cliente"), nullable=False, index=True)
    marca = Column(String(100), nullable=False)
    anio = Column(Integer, nullable=False)
    modelo = Column(String(100), nullable=False)
    placa = Column(String(20), nullable=False, unique=True, index=True)

    cliente = relationship("Cliente", back_populates="vehiculos")
    solicitudes = relationship("Solicitud", back_populates="vehiculo", cascade="all, delete-orphan")

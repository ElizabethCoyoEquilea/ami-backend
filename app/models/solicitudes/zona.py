from sqlalchemy import Column, Float, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Zona(Base):
    __tablename__ = "zona"

    id_zona = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True, index=True)
    descripcion = Column(Text, nullable=True)
    latitud_centro = Column(Float, nullable=False)
    longitud_centro = Column(Float, nullable=False)
    radio_aproximado = Column(Float, nullable=False)

    solicitudes = relationship("Solicitud", back_populates="zona")

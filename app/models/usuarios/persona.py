from sqlalchemy import Column, Integer, String, Date
from sqlalchemy.orm import relationship
from app.core.database import Base


class Persona(Base):
    __tablename__ = "persona"

    id_persona = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre_completo = Column(String(150), nullable=False)
    fecha_nacimiento = Column(Date, nullable=True)
    genero = Column(String(1), nullable=True)
    telefono = Column(String(20), nullable=True)
    documento = Column(String(50), nullable=True)

    usuario = relationship("User", back_populates="persona", uselist=False)
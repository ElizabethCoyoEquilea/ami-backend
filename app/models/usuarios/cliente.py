from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Cliente(Base):
    __tablename__ = "cliente"

    id_cliente = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, unique=True)
    codigo = Column(String(20), nullable=False, unique=True, index=True)

    usuario = relationship("User", back_populates="cliente")

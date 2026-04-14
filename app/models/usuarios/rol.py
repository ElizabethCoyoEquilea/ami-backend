from sqlalchemy import Boolean, Column, Integer, String, text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Rol(Base):
    __tablename__ = "rol"

    id_rol = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nombre = Column(String(50), nullable=False)
    descripcion = Column(String(255), nullable=True)
    activo = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    usuarios_roles = relationship("UsuarioRol", back_populates="rol")

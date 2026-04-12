from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class User(Base):
    __tablename__ = "usuario"

    id_usuario = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_persona = Column(Integer, ForeignKey("persona.id_persona"), nullable=False, unique=True)
    fecha_creacion = Column(DateTime, nullable=False, server_default=func.now())
    email = Column(String(100), unique=True, index=True, nullable=False)
    contrasena = Column(String(255), nullable=False)
    activo = Column(Boolean, default=True)

    persona = relationship("Persona", back_populates="usuario")
    usuarios_roles = relationship("UsuarioRol", back_populates="usuario")

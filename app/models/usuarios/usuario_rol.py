from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import relationship
from app.core.database import Base


class UsuarioRol(Base):
    __tablename__ = "usuario_rol"

    id_usuario_rol = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_rol = Column(Integer, ForeignKey("rol.id_rol"), nullable=False)
    fecha = Column(DateTime, nullable=False, server_default=func.now())
    activo = Column(Boolean, default=True)

    usuario = relationship("User", back_populates="usuarios_roles")
    rol = relationship("Rol", back_populates="usuarios_roles")

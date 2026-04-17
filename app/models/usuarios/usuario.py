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
    activo = Column(Boolean, default=False)
    codigo_verificacion_hash = Column(String(64), nullable=True)
    codigo_verificacion_expira_en = Column(DateTime, nullable=True)
    codigo_verificacion_intentos = Column(Integer, nullable=False, default=0)

    persona = relationship("Persona", back_populates="usuario")
    cliente = relationship("Cliente", back_populates="usuario", uselist=False)
    usuarios_roles = relationship("UsuarioRol", back_populates="usuario")
    talleres = relationship("Taller", back_populates="usuario")
    proveedores_servicio = relationship("ProveedorServicio", back_populates="usuario")

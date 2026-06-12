from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Especialidad(Base):
    __tablename__ = "especialidad"

    id_especialidad = Column(Integer, primary_key=True, autoincrement=True, index=True)
    codigo = Column(String(50), nullable=False, unique=True, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)

    catalogo_servicios = relationship("CatalogoServicio", back_populates="especialidad")
    proveedor_especialidades = relationship(
        "ProveedorEspecialidad",
        back_populates="especialidad",
        cascade="all, delete-orphan",
    )

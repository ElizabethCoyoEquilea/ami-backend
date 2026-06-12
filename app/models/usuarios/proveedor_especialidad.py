from sqlalchemy import Boolean, Column, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProveedorEspecialidad(Base):
    __tablename__ = "proveedor_especialidad"

    id_proveedor_especialidad = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_proveedor = Column(Integer, ForeignKey("proveedor_servicio.id_proveedor"), nullable=False, index=True)
    id_especialidad = Column(Integer, ForeignKey("especialidad.id_especialidad"), nullable=False, index=True)
    activo = Column(Boolean, nullable=False, default=True)

    proveedor_servicio = relationship(
        "ProveedorServicio",
        back_populates="proveedor_especialidades",
    )
    especialidad = relationship("Especialidad", back_populates="proveedor_especialidades")

    __table_args__ = (
        UniqueConstraint(
            "id_proveedor",
            "id_especialidad",
            name="uq_proveedor_especialidad_proveedor_especialidad",
        ),
    )

from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProveedorServicio(Base):
    __tablename__ = "proveedor_servicio"

    id_proveedor = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    id_taller = Column(Integer, ForeignKey("taller.id_taller"), nullable=False, index=True)
    estado = Column(String(50), nullable=True)

    usuario = relationship("User", back_populates="proveedores_servicio")
    taller = relationship("Taller", back_populates="proveedores_servicio")
    asignaciones = relationship("Asignacion", back_populates="proveedor_servicio")
    proveedor_especialidades = relationship(
        "ProveedorEspecialidad",
        back_populates="proveedor_servicio",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("id_usuario", "id_taller", name="uq_proveedor_servicio_usuario_taller"),
    )

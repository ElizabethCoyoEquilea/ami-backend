from sqlalchemy import Column, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class DetalleServicio(Base):
    __tablename__ = "detalle_servicio"

    id_detalle_servicio = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_servicio = Column(Integer, ForeignKey("servicio.id_servicio"), nullable=False, index=True)
    id_catalogo_servicio = Column(Integer, ForeignKey("catalogo_servicio.id_catalogo_servicio"), nullable=False, index=True)
    cantidad = Column(Integer, nullable=False)
    precio = Column(Numeric(12, 2), nullable=False)
    sub_total = Column(Numeric(12, 2), nullable=False)
    nombre = Column(String(150), nullable=False)
    observacion = Column(String(500), nullable=True)

    servicio = relationship("Servicio", back_populates="detalles_servicio")
    catalogo_servicio = relationship("CatalogoServicio", back_populates="detalles_servicio")

from sqlalchemy import Boolean, CheckConstraint, Column, Float, ForeignKey, Integer, String, Time
from sqlalchemy.orm import relationship

from app.core.database import Base


class Taller(Base):
    __tablename__ = "taller"

    id_taller = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False, index=True)
    nombre = Column(String(150), nullable=False)
    descripcion = Column(String(500), nullable=True)
    radio_cobertura = Column(Float, nullable=False)
    calificacion = Column(Float, nullable=False, default=0)
    direccion = Column(String(255), nullable=False)
    longitud = Column(Float, nullable=True)
    latitud = Column(Float, nullable=True)
    horario_inicio = Column(Time, nullable=False)
    horario_fin = Column(Time, nullable=False)
    estado = Column(String(10), nullable=False, default="cerrado")
    activo = Column(Boolean, nullable=False, default=True)

    usuario = relationship("User", back_populates="talleres")
    catalogo_servicios = relationship("CatalogoServicio", back_populates="taller")
    proveedores_servicio = relationship("ProveedorServicio", back_populates="taller")

    __table_args__ = (
        CheckConstraint("radio_cobertura >= 0", name="ck_taller_radio_cobertura_no_negativo"),
        CheckConstraint("calificacion >= 0 AND calificacion <= 5", name="ck_taller_calificacion_rango"),
        CheckConstraint("estado IN ('abierto', 'cerrado')", name="ck_taller_estado_valido"),
    )

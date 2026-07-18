from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class Servicio(Base):
    __tablename__ = "servicio"

    id_servicio = Column(Integer, primary_key=True, autoincrement=True, index=True)
    id_asignacion = Column(Integer, ForeignKey("asignacion.id_asignacion"), nullable=False, index=True)
    id_pago = Column(Integer, ForeignKey("pago.id_pago"), nullable=True, unique=True, index=True)
    total = Column(Numeric(12, 2), nullable=True, default=0)
    fecha_inicio = Column(DateTime, nullable=True)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(30), nullable=False, default="En curso")

    asignacion = relationship("Asignacion", back_populates="servicios")
    pago = relationship("Pago", back_populates="servicio", uselist=False)
    calificacion = relationship("Calificacion", back_populates="servicio", uselist=False, cascade="all, delete-orphan")
    calificacion_cliente = relationship("CalificacionCliente", back_populates="servicio", uselist=False, cascade="all, delete-orphan")
    detalles_servicio = relationship("DetalleServicio", back_populates="servicio", cascade="all, delete-orphan")

    @property
    def id_usuario_cliente(self) -> int | None:
        solicitud = self.asignacion.solicitud if self.asignacion else None
        vehiculo = solicitud.vehiculo if solicitud else None
        cliente = vehiculo.cliente if vehiculo else None
        return cliente.id_usuario if cliente else None

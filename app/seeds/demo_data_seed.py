from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from faker import Faker
from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.schema_updates import apply_schema_updates
from app.core.security import get_password_hash
from app.models.solicitudes.asignacion import Asignacion
from app.models.solicitudes.calificacion import Calificacion
from app.models.solicitudes.cotizacion import Invitacion
from app.models.solicitudes.detalle_servicio import DetalleServicio
from app.models.solicitudes.pago import Pago
from app.models.solicitudes.servicio import Servicio
from app.models.solicitudes.solicitud import Solicitud
from app.models.talleres.catalogo_servicio import CatalogoServicio
from app.models.talleres.especialidad import Especialidad
from app.models.talleres.taller import Taller
from app.models.usuarios.cliente import Cliente
from app.models.usuarios.persona import Persona
from app.models.usuarios.proveedor_especialidad import ProveedorEspecialidad
from app.models.usuarios.proveedor_servicio import ProveedorServicio
from app.models.usuarios.rol import Rol
from app.models.usuarios.usuario import User
from app.models.usuarios.usuario_rol import UsuarioRol
from app.models.usuarios.vehiculo import Vehiculo


fake = Faker("es_ES")
random.seed(42)
Faker.seed(42)

PASSWORD = "123456"
AYRTON_HISTORICAL_COMPLETED_SERVICES = 600

ROLE_ADMIN = "ADMINISTRADOR"
ROLE_PROVIDER = "PROVEEDOR DE SERVICIO"
ROLE_CLIENT = "CLIENTE"

AYRTON_EMAIL = "ayrton.daza.1230@gmail.com"
ELIZABETH_EMAIL = "cee777578@gmail.com"
AYRTON2_EMAIL = "ayrton.daza.1231@gmail.com"


def _role(db: Session, nombre: str) -> Rol:
    role = db.query(Rol).filter(Rol.nombre == nombre, Rol.activo.is_(True)).first()
    if not role:
        raise RuntimeError(
            f"No existe el rol activo '{nombre}'. Ejecuta primero los seeds de roles."
        )
    return role


def _user(
    db: Session,
    *,
    email: str,
    nombre: str,
    genero: str = "M",
    telefono: str | None = None,
    documento: str | None = None,
    fecha_nacimiento: date | None = None,
) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        user.activo = True
        user.codigo_verificacion_hash = None
        user.codigo_verificacion_expira_en = None
        user.codigo_verificacion_intentos = 0
        return user

    persona = Persona(
        nombre_completo=nombre,
        fecha_nacimiento=fecha_nacimiento or fake.date_of_birth(minimum_age=22, maximum_age=55),
        genero=genero,
        telefono=telefono or fake.msisdn()[:8],
        documento=documento or str(fake.unique.random_number(digits=8, fix_len=True)),
    )
    db.add(persona)
    db.flush()

    user = User(
        id_persona=persona.id_persona,
        email=email,
        contrasena=get_password_hash(PASSWORD),
        activo=True,
        codigo_verificacion_hash=None,
        codigo_verificacion_expira_en=None,
        codigo_verificacion_intentos=0,
    )
    db.add(user)
    db.flush()
    return user


def _ensure_user_role(
    db: Session,
    *,
    user: User,
    role: Rol,
    id_taller: int | None = None,
) -> UsuarioRol:
    user_role = (
        db.query(UsuarioRol)
        .filter(
            UsuarioRol.id_usuario == user.id_usuario,
            UsuarioRol.id_rol == role.id_rol,
            UsuarioRol.id_taller == id_taller,
        )
        .first()
    )
    if user_role:
        user_role.activo = True
        return user_role

    user_role = UsuarioRol(
        id_usuario=user.id_usuario,
        id_rol=role.id_rol,
        id_taller=id_taller,
        activo=True,
    )
    db.add(user_role)
    db.flush()
    return user_role


def _taller(db: Session, *, owner: User, nombre: str, index: int) -> Taller:
    tiempo_respuesta = 5 if nombre == "Taller Demo Ayrton" else min(60, 10 + (index * 10))
    taller = db.query(Taller).filter(Taller.nombre == nombre).first()
    if taller:
        taller.activo = True
        taller.tiempo_respuesta = tiempo_respuesta
        return taller

    taller = Taller(
        id_usuario=owner.id_usuario,
        nombre=nombre,
        descripcion=f"Taller demo especializado en {random.choice(['mecanica general', 'auxilio vial', 'diagnostico', 'electricidad'])}.",
        radio_cobertura=random.choice([8, 10, 12, 15, 20]),
        calificacion=round(random.uniform(3.8, 4.9), 1),
        direccion=fake.address()[:255],
        longitud=-63.18 + random.uniform(-0.08, 0.08),
        latitud=-17.78 + random.uniform(-0.08, 0.08),
        qr=None,
        tiempo_respuesta=tiempo_respuesta,
        horario_inicio=time(8, 0),
        horario_fin=time(18, 30),
        estado=random.choice(["abierto", "cerrado"]),
        activo=True,
    )
    db.add(taller)
    db.flush()
    return taller


def _cliente(db: Session, *, user: User, codigo: str) -> Cliente:
    cliente = db.query(Cliente).filter(Cliente.id_usuario == user.id_usuario).first()
    if cliente:
        return cliente

    existing = db.query(Cliente).filter(Cliente.codigo == codigo).first()
    if existing:
        codigo = f"CLI{user.id_usuario:06d}"

    cliente = Cliente(id_usuario=user.id_usuario, codigo=codigo)
    db.add(cliente)
    db.flush()
    return cliente


def _vehiculo(
    db: Session,
    *,
    cliente: Cliente,
    marca: str,
    modelo: str,
    anio: int,
    placa: str,
) -> Vehiculo:
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placa == placa).first()
    if vehiculo:
        return vehiculo

    vehiculo = Vehiculo(
        id_cliente=cliente.id_cliente,
        marca=marca,
        modelo=modelo,
        anio=anio,
        placa=placa,
    )
    db.add(vehiculo)
    db.flush()
    return vehiculo


def _especialidad(
    db: Session,
    *,
    codigo: str,
    nombre: str,
    descripcion: str | None = None,
) -> Especialidad:
    especialidad = db.query(Especialidad).filter(Especialidad.codigo == codigo).first()
    if especialidad:
        return especialidad

    especialidad = Especialidad(
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion,
    )
    db.add(especialidad)
    db.flush()
    return especialidad


def _catalogo(db: Session, taller: Taller) -> list[CatalogoServicio]:
    especialidades = {
        "Mantenimiento": _especialidad(
            db,
            codigo="MANTENIMIENTO",
            nombre="Mantenimiento preventivo",
            descripcion="Mantenimiento preventivo",
        ),
        "Diagnostico": _especialidad(
            db,
            codigo="DIAGNOSTICO",
            nombre="Diagnostico automotriz",
            descripcion="Diagnostico automotriz",
        ),
        "Electrico": _especialidad(
            db,
            codigo="ELECTRICIDAD",
            nombre="Electricidad automotriz",
            descripcion="Electricidad automotriz",
        ),
        "Auxilio vial": _especialidad(
            db,
            codigo="REMOLQUE",
            nombre="Grua y traslado",
            descripcion="Grua y traslado",
        ),
        "Mecanica": _especialidad(
            db,
            codigo="MECANICA_GENERAL",
            nombre="Mecanica general",
            descripcion="Mecanica general",
        ),
        "Neumaticos": _especialidad(
            db,
            codigo="NEUMATICOS",
            nombre="Neumaticos y llantas",
            descripcion="Neumaticos y llantas",
        ),
        "Frenos": _especialidad(
            db,
            codigo="FRENOS",
            nombre="Sistema de frenos",
            descripcion="Sistema de frenos",
        ),
        "Motor": _especialidad(
            db,
            codigo="MOTOR",
            nombre="Motor",
            descripcion="Motor",
        ),
    }
    base_items = [
        ("Cambio de aceite", "Mantenimiento", 90),
        ("Diagnostico computarizado", "Diagnostico", 120),
        ("Cambio de bateria", "Electrico", 260),
        ("Auxilio por grua", "Auxilio vial", 180),
        ("Cambio de llanta", "Neumaticos", 60),
        ("Revision de frenos", "Frenos", 140),
        ("Cambio de bujias", "Motor", 110),
        ("Revision electrica", "Electrico", 130),
    ]
    catalogo = []
    for idx, (nombre, especialidad_nombre, precio) in enumerate(base_items, start=1):
        item = (
            db.query(CatalogoServicio)
            .filter(
                CatalogoServicio.id_taller == taller.id_taller,
                CatalogoServicio.nombre == nombre,
            )
            .first()
        )
        if not item:
            item = CatalogoServicio(
                id_taller=taller.id_taller,
                id_especialidad=especialidades[especialidad_nombre].id_especialidad,
                nombre=nombre,
                descripcion=f"{nombre} realizado por {taller.nombre}",
                precio_estandar=float(precio + idx * 3),
                estado="activo" if idx <= 7 else "inactivo",
            )
            db.add(item)
            db.flush()
        catalogo.append(item)
    return catalogo


def _proveedor(
    db: Session,
    *,
    user: User,
    taller: Taller,
    role_provider: Rol,
    estado: str = "Disponible",
) -> ProveedorServicio:
    _ensure_user_role(db, user=user, role=role_provider, id_taller=taller.id_taller)
    proveedor = (
        db.query(ProveedorServicio)
        .filter(
            ProveedorServicio.id_usuario == user.id_usuario,
            ProveedorServicio.id_taller == taller.id_taller,
        )
        .first()
    )
    if proveedor:
        proveedor.estado = estado
        return proveedor

    proveedor = ProveedorServicio(
        id_usuario=user.id_usuario,
        id_taller=taller.id_taller,
        estado=estado,
    )
    db.add(proveedor)
    db.flush()

    especialidad = random.choice(db.query(Especialidad).all())
    proveedor_especialidad = ProveedorEspecialidad(
        id_proveedor=proveedor.id_proveedor,
        id_especialidad=especialidad.id_especialidad,
        activo=True,
    )
    db.add(proveedor_especialidad)
    db.flush()
    return proveedor


def _crear_flujo_servicio(
    db: Session,
    *,
    vehiculo: Vehiculo,
    taller: Taller,
    proveedor: ProveedorServicio | None,
    catalogo: list[CatalogoServicio],
    idx: int,
    estado_flujo: str,
) -> None:
    descripcion = f"DEMO solicitud {idx:04d} - {random.choice(['ruido en motor', 'no arranca', 'falla electrica', 'mantenimiento preventivo'])}"
    existe = db.query(Solicitud).filter(Solicitud.descripcion == descripcion).first()
    if existe:
        return

    solicitud_estado = {
        "pendiente": "pendiente",
        "cotizada": "enviado",
        "asignada": "aceptada",
        "curso": "aceptada",
        "pendiente_pago": "aceptada",
        "pagado": "aceptada",
    }[estado_flujo]

    solicitud = Solicitud(
        id_vehiculo=vehiculo.id_vehiculo,
        descripcion=descripcion,
        latitud=-17.78 + random.uniform(-0.05, 0.05),
        direccion=fake.street_address()[:255],
        longitud=-63.18 + random.uniform(-0.05, 0.05),
        fecha=datetime.now() - timedelta(days=random.randint(1, 45)),
        prioridad=random.choice(["baja", "media", "alta"]),
        observaciones=None,
        audio=None,
        imagenes=None,
        estado=solicitud_estado,
    )
    db.add(solicitud)
    db.flush()

    if estado_flujo == "pendiente":
        return

    invitacion_estado = {
        "cotizada": "enviado",
        "asignada": "aceptada",
        "curso": "aceptada",
        "pendiente_pago": "aceptada",
        "pagado": "aceptada",
    }[estado_flujo]
    invitacion = Invitacion(
        id_solicitud=solicitud.id_solicitud,
        id_taller=taller.id_taller,
        numero_ronda=solicitud.ronda_actual or 1,
        estado=invitacion_estado,
    )
    db.add(invitacion)
    db.flush()

    if estado_flujo == "cotizada":
        return

    asignacion_estado = {
        "asignada": "enviada",
        "curso": "Asignado",
        "pendiente_pago": "Asignado",
        "pagado": "Asignado",
    }[estado_flujo]
    asignacion = Asignacion(
        id_solicitud=solicitud.id_solicitud,
        id_taller=taller.id_taller,
        id_proveedor=proveedor.id_proveedor if proveedor else None,
        fecha=datetime.now() - timedelta(days=random.randint(1, 30)),
        estado=asignacion_estado,
    )
    db.add(asignacion)
    db.flush()

    if estado_flujo == "asignada":
        if proveedor:
            proveedor.estado = "Disponible"
        return

    servicio_estado = {
        "curso": "En curso",
        "pendiente_pago": "Pendiente de pago",
        "pagado": "pagado",
    }[estado_flujo]
    servicio = Servicio(
        id_asignacion=asignacion.id_asignacion,
        id_pago=None,
        total=Decimal("0.00"),
        fecha_inicio=datetime.now() - timedelta(days=random.randint(1, 20), hours=2),
        fecha_fin=None if estado_flujo == "curso" else datetime.now() - timedelta(days=random.randint(0, 10)),
        estado=servicio_estado,
    )
    db.add(servicio)
    db.flush()

    if estado_flujo == "curso":
        if proveedor:
            proveedor.estado = "Ocupado"
        return

    total = Decimal("0.00")
    for item in random.sample(catalogo[:7], k=random.randint(2, 4)):
        cantidad = random.randint(1, 2)
        precio = Decimal(str(item.precio_estandar))
        sub_total = precio * Decimal(cantidad)
        total += sub_total
        detalle = DetalleServicio(
            id_servicio=servicio.id_servicio,
            id_catalogo_servicio=item.id_catalogo_servicio,
            cantidad=cantidad,
            precio=precio,
            sub_total=sub_total,
            nombre=item.nombre,
            observacion=random.choice([None, "Trabajo realizado sin observaciones", "Incluye repuestos menores"]),
        )
        db.add(detalle)

    pago = Pago(
        monto=total,
        estado="pagado" if estado_flujo == "pagado" else "pendiente",
        metodo=random.choice(["qr", "efectivo", "tarjeta"]) if estado_flujo == "pagado" else None,
        fecha=datetime.now() - timedelta(days=random.randint(0, 8)) if estado_flujo == "pagado" else None,
    )
    db.add(pago)
    db.flush()

    servicio.total = total
    servicio.id_pago = pago.id_pago

    if proveedor:
        proveedor.estado = "Disponible" if estado_flujo == "pagado" else "Ocupado"

    if estado_flujo == "pagado":
        calificacion = Calificacion(
            id_servicio=servicio.id_servicio,
            puntuacion=random.randint(3, 5),
            comentario=random.choice([
                "Buen servicio y puntualidad.",
                "Trabajo correcto.",
                "Atencion rapida.",
                "Recomendado.",
            ]),
            fecha=datetime.now() - timedelta(days=random.randint(0, 7)),
        )
        db.add(calificacion)


def _crear_servicios_realizados_ayrton(
    db: Session,
    *,
    taller: Taller,
    proveedores: list[ProveedorServicio],
    catalogo: list[CatalogoServicio],
    clientes: list[tuple[Cliente, list[Vehiculo]]],
    cantidad: int = AYRTON_HISTORICAL_COMPLETED_SERVICES,
) -> None:
    if not proveedores:
        raise RuntimeError("El taller de Ayrton no tiene proveedores para crear servicios historicos.")
    if not clientes:
        raise RuntimeError("No hay clientes con vehiculos para crear servicios historicos.")

    rng = random.Random(20250427)
    items_activos = [item for item in catalogo if item.estado == "activo"]
    if not items_activos:
        raise RuntimeError("El taller de Ayrton no tiene catalogo activo para crear detalles.")

    inicio_rango = datetime(2025, 1, 1, 8, 0)
    fin_rango = datetime(2026, 4, 27, 18, 0)
    rango_segundos = int((fin_rango - inicio_rango).total_seconds())

    for idx in range(1, cantidad + 1):
        descripcion = f"DEMO AYRTON servicio realizado historico {idx:04d}"
        existe = db.query(Solicitud).filter(Solicitud.descripcion == descripcion).first()
        if existe:
            continue

        cliente, vehiculos = clientes[(idx - 1) % len(clientes)]
        if not vehiculos:
            continue

        vehiculo = vehiculos[(idx + rng.randint(0, len(vehiculos) - 1)) % len(vehiculos)]
        proveedor = proveedores[(idx - 1) % len(proveedores)]
        fecha_fin = inicio_rango + timedelta(seconds=rng.randint(0, rango_segundos))
        fecha_inicio = fecha_fin - timedelta(hours=rng.randint(1, 7), minutes=rng.randint(0, 45))
        fecha_solicitud = fecha_inicio - timedelta(days=rng.randint(0, 3), hours=rng.randint(1, 12))

        detalles_catalogo = rng.sample(items_activos, k=rng.randint(2, min(5, len(items_activos))))
        total = Decimal("0.00")
        detalles: list[tuple[CatalogoServicio, int, Decimal, Decimal]] = []
        for item in detalles_catalogo:
            cantidad_item = rng.randint(1, 3)
            precio = Decimal(str(item.precio_estandar)).quantize(Decimal("0.01"))
            sub_total = precio * Decimal(cantidad_item)
            total += sub_total
            detalles.append((item, cantidad_item, precio, sub_total))

        solicitud = Solicitud(
            id_vehiculo=vehiculo.id_vehiculo,
            descripcion=descripcion,
            latitud=-17.78 + rng.uniform(-0.06, 0.06),
            direccion=fake.street_address()[:255],
            longitud=-63.18 + rng.uniform(-0.06, 0.06),
            fecha=fecha_solicitud,
            prioridad=rng.choice(["baja", "media", "alta"]),
            observaciones=rng.choice([None, "Servicio historico generado para pruebas."]),
            audio=None,
            imagenes=None,
            estado="aceptada",
        )
        db.add(solicitud)
        db.flush()

        invitacion = Invitacion(
            id_solicitud=solicitud.id_solicitud,
            id_taller=taller.id_taller,
            numero_ronda=solicitud.ronda_actual or 1,
            estado="aceptada",
        )
        db.add(invitacion)
        db.flush()

        asignacion = Asignacion(
            id_solicitud=solicitud.id_solicitud,
            id_taller=taller.id_taller,
            id_proveedor=proveedor.id_proveedor,
            fecha=fecha_inicio - timedelta(minutes=rng.randint(10, 90)),
            estado="Asignado",
        )
        db.add(asignacion)
        db.flush()

        pago = Pago(
            monto=total,
            estado="pagado",
            metodo=rng.choice(["qr", "efectivo", "tarjeta"]),
            fecha=fecha_fin + timedelta(minutes=rng.randint(5, 90)),
        )
        db.add(pago)
        db.flush()

        servicio = Servicio(
            id_asignacion=asignacion.id_asignacion,
            id_pago=pago.id_pago,
            total=total,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            estado="pagado",
        )
        db.add(servicio)
        db.flush()

        for item, cantidad_item, precio, sub_total in detalles:
            detalle = DetalleServicio(
                id_servicio=servicio.id_servicio,
                id_catalogo_servicio=item.id_catalogo_servicio,
                cantidad=cantidad_item,
                precio=precio,
                sub_total=sub_total,
                nombre=item.nombre,
                observacion=rng.choice([
                    "Servicio completado.",
                    "Trabajo finalizado y probado.",
                    "Cliente conforme con el servicio.",
                    None,
                ]),
            )
            db.add(detalle)

        calificacion = Calificacion(
            id_servicio=servicio.id_servicio,
            puntuacion=rng.choices([3, 4, 5], weights=[1, 4, 8], k=1)[0],
            comentario=rng.choice([
                "Muy buen servicio.",
                "Atencion puntual y clara.",
                "Trabajo realizado correctamente.",
                "Recomendado.",
                "Servicio rapido.",
            ]),
            fecha=fecha_fin + timedelta(days=rng.randint(0, 4), hours=rng.randint(1, 8)),
        )
        db.add(calificacion)

    for proveedor in proveedores:
        proveedor.estado = "Disponible"


def run_demo_seed() -> None:
    Base.metadata.create_all(bind=engine)
    apply_schema_updates()
    db = SessionLocal()
    try:
        role_admin = _role(db, ROLE_ADMIN)
        role_provider = _role(db, ROLE_PROVIDER)
        role_client = _role(db, ROLE_CLIENT)

        ayrton = _user(
            db,
            email=AYRTON_EMAIL,
            nombre="Ayrton Daza Miranda",
            genero="M",
            telefono="61524977",
            documento="12345678",
            fecha_nacimiento=date(2002, 12, 10),
        )
        elizabeth = _user(
            db,
            email=ELIZABETH_EMAIL,
            nombre="Elizabeth Coyo Equilea",
            genero="F",
            telefono="71687109",
            documento="12345679",
            fecha_nacimiento=date(2001, 12, 31),
        )
        ayrton2 = _user(
            db,
            email=AYRTON2_EMAIL,
            nombre="Ayrton2 Daza Miranda",
            genero="M",
            telefono="71687110",
            documento="12345680",
            fecha_nacimiento=date(2002, 12, 11),
        )

        admin_users = [ayrton]
        for i in range(1, 5):
            admin_users.append(
                _user(
                    db,
                    email=f"demo.admin{i}@ami-demo.com",
                    nombre=fake.name(),
                    genero=random.choice(["M", "F"]),
                )
            )

        talleres: list[Taller] = []
        catalogos: dict[int, list[CatalogoServicio]] = {}
        proveedores_por_taller: dict[int, list[ProveedorServicio]] = {}

        for idx, admin in enumerate(admin_users, start=1):
            taller_nombre = "Taller Demo Ayrton" if admin.email == AYRTON_EMAIL else f"Taller Demo {idx}"
            taller = _taller(db, owner=admin, nombre=taller_nombre, index=idx)
            _ensure_user_role(db, user=admin, role=role_admin, id_taller=taller.id_taller)
            talleres.append(taller)
            catalogos[taller.id_taller] = _catalogo(db, taller)

            proveedores = []
            if admin.email == AYRTON_EMAIL:
                proveedores.append(
                    _proveedor(
                        db,
                        user=elizabeth,
                        taller=taller,
                        role_provider=role_provider,
                        estado="Disponible",
                    )
                )

            target_count = random.randint(5, 10)
            while len(proveedores) < target_count:
                n = len(proveedores) + 1
                provider_user = _user(
                    db,
                    email=f"demo.proveedor.t{idx}.{n}@ami-demo.com",
                    nombre=fake.name(),
                    genero=random.choice(["M", "F"]),
                )
                proveedores.append(
                    _proveedor(
                        db,
                        user=provider_user,
                        taller=taller,
                        role_provider=role_provider,
                        estado="Disponible",
                    )
                )
            proveedores_por_taller[taller.id_taller] = proveedores

        clients: list[tuple[Cliente, list[Vehiculo]]] = []
        _ensure_user_role(db, user=ayrton2, role=role_client)
        ayrton2_cliente = _cliente(db, user=ayrton2, codigo="CLI-DEMO-AYRTON2")
        ayrton2_vehiculo = _vehiculo(
            db,
            cliente=ayrton2_cliente,
            marca="Toyota",
            modelo="Corolla",
            anio=2018,
            placa="AMI-0001",
        )
        clients.append((ayrton2_cliente, [ayrton2_vehiculo]))

        for i in range(1, 31):
            user = _user(
                db,
                email=f"demo.cliente{i}@ami-demo.com",
                nombre=fake.name(),
                genero=random.choice(["M", "F"]),
            )
            _ensure_user_role(db, user=user, role=role_client)
            cliente = _cliente(db, user=user, codigo=f"CLI-DEMO-{i:04d}")
            vehiculos = []
            for j in range(random.randint(1, 2)):
                vehiculos.append(
                    _vehiculo(
                        db,
                        cliente=cliente,
                        marca=random.choice(["Toyota", "Nissan", "Suzuki", "Hyundai", "Kia", "Ford"]),
                        modelo=random.choice(["Corolla", "Sentra", "Swift", "Tucson", "Rio", "Ranger"]),
                        anio=random.randint(2012, 2024),
                        placa=f"DEM-{i:03d}{j}",
                    )
                )
            clients.append((cliente, vehiculos))

        flujo_idx = 1
        ayrton_taller = talleres[0]
        for estado in ["pagado", "pendiente_pago", "curso", "asignada"]:
            _crear_flujo_servicio(
                db,
                vehiculo=ayrton2_vehiculo,
                taller=ayrton_taller,
                proveedor=proveedores_por_taller[ayrton_taller.id_taller][0],
                catalogo=catalogos[ayrton_taller.id_taller],
                idx=flujo_idx,
                estado_flujo=estado,
            )
            flujo_idx += 1

        _crear_servicios_realizados_ayrton(
            db,
            taller=ayrton_taller,
            proveedores=proveedores_por_taller[ayrton_taller.id_taller],
            catalogo=catalogos[ayrton_taller.id_taller],
            clientes=clients,
        )

        estados = ["pendiente", "cotizada", "asignada", "curso", "pendiente_pago", "pagado"]
        for cliente, vehiculos in clients[1:]:
            for _ in range(random.randint(1, 3)):
                taller = random.choice(talleres)
                proveedores = proveedores_por_taller[taller.id_taller]
                estado = random.choices(
                    estados,
                    weights=[1, 1, 2, 2, 3, 5],
                    k=1,
                )[0]
                _crear_flujo_servicio(
                    db,
                    vehiculo=random.choice(vehiculos),
                    taller=taller,
                    proveedor=random.choice(proveedores),
                    catalogo=catalogos[taller.id_taller],
                    idx=flujo_idx,
                    estado_flujo=estado,
                )
                flujo_idx += 1

        db.commit()
        print(
            "Demo seed completado: 5 admins/talleres, catalogos, proveedores, clientes, vehiculos, solicitudes, invitaciones, asignaciones, servicios, pagos y calificaciones."
        )
        print(f"Password demo para usuarios creados: {PASSWORD}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_demo_seed()

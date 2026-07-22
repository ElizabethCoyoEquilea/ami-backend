import os
import psycopg2
import datetime
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
PASSWORD_HASH = pwd_context.hash("123456")

DB_URL = "postgresql://ami_db_5q23_user:AxxhfK0cFa8qYgVb0jt2CNZtCWG3be1m@dpg-d9felsjh523c73f2u160-a.oregon-postgres.render.com:5432/ami_db_5q23?sslmode=require"

def seed_database():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    print("Conectado a la base de datos de la nube en Render...")

    # Helper to get or create user
    def create_user_and_persona(nombre_completo, email, telefono, documento, genero="M", fecha_nac="1995-05-15"):
        cur.execute("SELECT id_usuario FROM usuario WHERE LOWER(email) = LOWER(%s)", (email,))
        existing = cur.fetchone()
        if existing:
            print(f"Usuario {email} ya existe (id_usuario: {existing[0]}), omitiendo creación.")
            return existing[0]

        cur.execute("""
            INSERT INTO persona (nombre_completo, fecha_nacimiento, genero, telefono, documento)
            VALUES (%s, %s, %s, %s, %s) RETURNING id_persona
        """, (nombre_completo, fecha_nac, genero, telefono, documento))
        id_persona = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO usuario (id_persona, email, contrasena, activo, fecha_creacion, codigo_verificacion_intentos)
            VALUES (%s, %s, %s, True, NOW(), 0) RETURNING id_usuario
        """, (id_persona, email, PASSWORD_HASH))
        id_usuario = cur.fetchone()[0]
        return id_usuario

    # 1. ADMINS & TALLERES (3 Admins, 3 Talleres)
    print("\n--- Creando Administradores y Talleres ---")
    admin_data = [
        {
            "email": "admin.juan@gmail.com",
            "nombre": "Juan Carlos Administrador",
            "telef": "77112233",
            "doc": "1122334",
            "taller_nombre": "Taller Mecánico San José",
            "taller_desc": "Especialistas en mecánica general, electricidad y frenos. Atención 24/7.",
            "taller_dir": "Av. Banzer 4to Anillo #402",
            "lat": -17.7562,
            "lng": -63.1784,
            "calif": 4.8
        },
        {
            "email": "admin.carlos@gmail.com",
            "nombre": "Carlos Roberto Administrador",
            "telef": "77223344",
            "doc": "2233445",
            "taller_nombre": "Auxilio y Grúas Expreso Central",
            "taller_desc": "Servicio de grúas urbanas, cambio de llantas y baterías de emergencia.",
            "taller_dir": "Av. Busch 3er Anillo #125",
            "lat": -17.7812,
            "lng": -63.1912,
            "calif": 4.9
        },
        {
            "email": "admin.roberto@gmail.com",
            "nombre": "Roberto Mario Administrador",
            "telef": "77334455",
            "doc": "3344556",
            "taller_nombre": "Automecánica Pro Santa Cruz",
            "taller_desc": "Diagnóstico computarizado, reparación de motores y mantenimiento.",
            "taller_dir": "Av. Doble Vía La Guardia 5to Anillo",
            "lat": -17.8105,
            "lng": -63.2050,
            "calif": 4.7
        }
    ]

    taller_ids = []
    for adm in admin_data:
        id_u = create_user_and_persona(adm["nombre"], adm["email"], adm["telef"], adm["doc"])
        
        # Insert user role
        cur.execute("SELECT id_usuario_rol FROM usuario_rol WHERE id_usuario = %s AND id_rol = 1", (id_u,))
        if not cur.fetchone():
            cur.execute("INSERT INTO usuario_rol (id_usuario, id_rol, fecha, activo) VALUES (%s, 1, NOW(), True)", (id_u,))

        # Insert taller (estado = 'abierto')
        cur.execute("SELECT id_taller FROM taller WHERE id_usuario = %s", (id_u,))
        existing_t = cur.fetchone()
        if existing_t:
            id_t = existing_t[0]
        else:
            cur.execute("""
                INSERT INTO taller (id_usuario, nombre, descripcion, direccion, latitud, longitud, radio_cobertura, tiempo_respuesta, calificacion, horario_inicio, horario_fin, estado, activo)
                VALUES (%s, %s, %s, %s, %s, %s, 15.0, 20, %s, '08:00:00', '22:00:00', 'abierto', True) RETURNING id_taller
            """, (id_u, adm["taller_nombre"], adm["taller_desc"], adm["taller_dir"], adm["lat"], adm["lng"], adm["calif"]))
            id_t = cur.fetchone()[0]
        
        # Link taller to usuario_rol
        cur.execute("UPDATE usuario_rol SET id_taller = %s WHERE id_usuario = %s AND id_rol = 1", (id_t, id_u))
        taller_ids.append(id_t)
        print(f"Taller registrado: {adm['taller_nombre']} (ID: {id_t})")

    # 2. PROVEEDORES / MECANICOS (4 Proveedores para los 3 talleres)
    print("\n--- Creando Proveedores / Mecánicos ---")
    prov_data = [
        # Taller 1 (San José) tiene 2 proveedores
        {"email": "prov.martin@gmail.com", "nombre": "Martín Suárez", "telef": "78111222", "doc": "4455661", "taller_id": taller_ids[0]},
        {"email": "prov.luis@gmail.com", "nombre": "Luis Fernando Roca", "telef": "78222333", "doc": "4455662", "taller_id": taller_ids[0]},
        # Taller 2 tiene 1 proveedor
        {"email": "prov.diego@gmail.com", "nombre": "Diego Flores", "telef": "78333444", "doc": "4455663", "taller_id": taller_ids[1]},
        # Taller 3 tiene 1 proveedor
        {"email": "prov.mario@gmail.com", "nombre": "Mario Alberto Paz", "telef": "78444555", "doc": "4455664", "taller_id": taller_ids[2]},
    ]

    proveedor_ids = []
    for prv in prov_data:
        id_u = create_user_and_persona(prv["nombre"], prv["email"], prv["telef"], prv["doc"])
        
        # Insert user role
        cur.execute("SELECT id_usuario_rol FROM usuario_rol WHERE id_usuario = %s AND id_rol = 2", (id_u,))
        if not cur.fetchone():
            cur.execute("INSERT INTO usuario_rol (id_usuario, id_rol, id_taller, fecha, activo) VALUES (%s, 2, %s, NOW(), True)", (id_u, prv["taller_id"]))

        # Insert proveedor_servicio
        cur.execute("SELECT id_proveedor FROM proveedor_servicio WHERE id_usuario = %s", (id_u,))
        existing_p = cur.fetchone()
        if existing_p:
            id_p = existing_p[0]
        else:
            cur.execute("""
                INSERT INTO proveedor_servicio (id_usuario, id_taller, estado)
                VALUES (%s, %s, 'Disponible') RETURNING id_proveedor
            """, (id_u, prv["taller_id"]))
            id_p = cur.fetchone()[0]
        proveedor_ids.append((id_p, prv["taller_id"]))
        print(f"Proveedor registrado: {prv['nombre']} ({prv['email']}) -> Taller ID: {prv['taller_id']}")

    # 3. CLIENTES / USUARIOS (10 Clientes)
    print("\n--- Creando 10 Clientes ---")
    cliente_data = [
        {"email": "usuario.pedro@gmail.com", "nombre": "Pedro Morales", "telef": "71000001", "doc": "6000001"},
        {"email": "usuario.lucas@gmail.com", "nombre": "Lucas Torrez", "telef": "71000002", "doc": "6000002"},
        {"email": "usuario.mateo@gmail.com", "nombre": "Mateo Aguilera", "telef": "71000003", "doc": "6000003"},
        {"email": "usuario.daniel@gmail.com", "nombre": "Daniel Mendoza", "telef": "71000004", "doc": "6000004"},
        {"email": "usuario.andres@gmail.com", "nombre": "Andrés Vargas", "telef": "71000005", "doc": "6000005"},
        {"email": "usuario.gabriel@gmail.com", "nombre": "Gabriel Rivas", "telef": "71000006", "doc": "6000006"},
        {"email": "usuario.fernando@gmail.com", "nombre": "Fernando Justiniano", "telef": "71000007", "doc": "6000007"},
        {"email": "usuario.adrian@gmail.com", "nombre": "Adrián Saucedo", "telef": "71000008", "doc": "6000008"},
        {"email": "usuario.javier@gmail.com", "nombre": "Javier Camacho", "telef": "71000009", "doc": "6000009"},
        {"email": "usuario.rodrigo@gmail.com", "nombre": "Rodrigo Hurtado", "telef": "71000010", "doc": "6000010"},
    ]

    cliente_ids = []
    for idx, cli in enumerate(cliente_data, start=1):
        id_u = create_user_and_persona(cli["nombre"], cli["email"], cli["telef"], cli["doc"])
        
        # Insert user role
        cur.execute("SELECT id_usuario_rol FROM usuario_rol WHERE id_usuario = %s AND id_rol = 3", (id_u,))
        if not cur.fetchone():
            cur.execute("INSERT INTO usuario_rol (id_usuario, id_rol, fecha, activo) VALUES (%s, 3, NOW(), True)", (id_u,))

        # Insert cliente
        cur.execute("SELECT id_cliente FROM cliente WHERE id_usuario = %s", (id_u,))
        existing_c = cur.fetchone()
        if existing_c:
            id_c = existing_c[0]
        else:
            cur.execute("""
                INSERT INTO cliente (id_usuario, codigo)
                VALUES (%s, %s) RETURNING id_cliente
            """, (id_u, f"CLI-{idx:03d}"))
            id_c = cur.fetchone()[0]
        cliente_ids.append(id_c)
        print(f"Cliente registrado: {cli['nombre']} ({cli['email']}) -> ID Cliente: {id_c}")

    # 4. VEHICULOS (Asignados a los 10 clientes)
    print("\n--- Registrando Vehículos ---")
    vehiculos_data = [
        {"cliente_id": cliente_ids[0], "marca": "Toyota", "modelo": "Corolla", "anio": 2021, "placa": "3045-ABC"},
        {"cliente_id": cliente_ids[0], "marca": "Suzuki", "modelo": "Swift", "anio": 2020, "placa": "4512-XYZ"},
        {"cliente_id": cliente_ids[1], "marca": "Nissan", "modelo": "Frontier", "anio": 2019, "placa": "1289-DEF"},
        {"cliente_id": cliente_ids[2], "marca": "Hyundai", "modelo": "Tucson", "anio": 2022, "placa": "5678-GHI"},
        {"cliente_id": cliente_ids[3], "marca": "Honda", "modelo": "Civic", "anio": 2020, "placa": "9012-JKL"},
        {"cliente_id": cliente_ids[4], "marca": "Ford", "modelo": "Ranger", "anio": 2018, "placa": "3456-MNO"},
        {"cliente_id": cliente_ids[5], "marca": "Kia", "modelo": "Sportage", "anio": 2021, "placa": "7890-PQR"},
        {"cliente_id": cliente_ids[6], "marca": "Volkswagen", "modelo": "Gol", "anio": 2019, "placa": "2345-STU"},
        {"cliente_id": cliente_ids[7], "marca": "Chevrolet", "modelo": "Tracker", "anio": 2022, "placa": "6789-VWX"},
        {"cliente_id": cliente_ids[8], "marca": "Mitsubishi", "modelo": "L200", "anio": 2020, "placa": "1234-YZA"},
        {"cliente_id": cliente_ids[9], "marca": "Suzuki", "modelo": "Vitara", "anio": 2021, "placa": "5678-BCD"},
    ]

    vehiculo_ids = []
    for v in vehiculos_data:
        cur.execute("SELECT id_vehiculo FROM vehiculo WHERE placa = %s", (v["placa"],))
        existing_v = cur.fetchone()
        if existing_v:
            id_v = existing_v[0]
        else:
            cur.execute("""
                INSERT INTO vehiculo (id_cliente, marca, modelo, anio, placa)
                VALUES (%s, %s, %s, %s, %s) RETURNING id_vehiculo
            """, (v["cliente_id"], v["marca"], v["modelo"], v["anio"], v["placa"]))
            id_v = cur.fetchone()[0]
        vehiculo_ids.append(id_v)
        print(f"Vehículo registrado: {v['marca']} {v['modelo']} [{v['placa']}] -> Cliente ID: {v['cliente_id']}")

    # 5. CATALOGO DE SERVICIOS POR TALLER
    print("\n--- Registrando Catálogo de Servicios por Taller ---")
    catalogos_data = [
        # Taller 1 (San José)
        {"taller_id": taller_ids[0], "esp_id": 1, "nombre": "Diagnóstico y Ajuste Mecánico", "desc": "Revisión completa de componentes mecánicos.", "precio": 120.0},
        {"taller_id": taller_ids[0], "esp_id": 2, "nombre": "Paso de Corriente y Diagnóstico Batería", "desc": "Auxilio eléctrico y batería en sitio.", "precio": 50.0},
        {"taller_id": taller_ids[0], "esp_id": 4, "nombre": "Revisión y Cambio de Pastillas de Freno", "desc": "Mantenimiento de sistema de frenado.", "precio": 90.0},
        {"taller_id": taller_ids[0], "esp_id": 10, "nombre": "Apertura de Puerta de Vehículo", "desc": "Cerrajería automotriz de emergencia.", "precio": 80.0},
        
        # Taller 2 (Grúas Expreso)
        {"taller_id": taller_ids[1], "esp_id": 12, "nombre": "Servicio de Grúa Urbana", "desc": "Remolque de vehículo dentro del radio urbano.", "precio": 180.0},
        {"taller_id": taller_ids[1], "esp_id": 3, "nombre": "Cambio y Reparación de Llanta", "desc": "Reparación de pinchazos y cambio de repuesto.", "precio": 60.0},
        {"taller_id": taller_ids[1], "esp_id": 2, "nombre": "Recarga y Reemplazo de Batería", "desc": "Instalación de batería nueva de auxilio.", "precio": 70.0},

        # Taller 3 (Automecánica Pro)
        {"taller_id": taller_ids[2], "esp_id": 5, "nombre": "Auxilio de Sobrecalentamiento de Motor", "desc": "Diagnóstico y control de temperatura de motor.", "precio": 150.0},
        {"taller_id": taller_ids[2], "esp_id": 6, "nombre": "Reparación de Fuga de Refrigerante", "desc": "Reparación de mangueras y fugas de radiador.", "precio": 110.0},
        {"taller_id": taller_ids[2], "esp_id": 9, "nombre": "Mantenimiento Preventivo de Emergencia", "desc": "Cambio de aceite y filtros rápida atención.", "precio": 130.0},
    ]

    catalogo_ids = []
    for cat in catalogos_data:
        cur.execute("SELECT id_catalogo_servicio FROM catalogo_servicio WHERE id_taller = %s AND nombre = %s", (cat["taller_id"], cat["nombre"]))
        existing_cat = cur.fetchone()
        if existing_cat:
            id_cat = existing_cat[0]
        else:
            cur.execute("""
                INSERT INTO catalogo_servicio (id_taller, id_especialidad, nombre, descripcion, precio_estandar, estado, fecha_creacion)
                VALUES (%s, %s, %s, %s, %s, 'activo', NOW()) RETURNING id_catalogo_servicio
            """, (cat["taller_id"], cat["esp_id"], cat["nombre"], cat["desc"], cat["precio"]))
            id_cat = cur.fetchone()[0]
        catalogo_ids.append(id_cat)
        print(f"Servicio en Catálogo: {cat['nombre']} ({cat['precio']} Bs) -> Taller ID: {cat['taller_id']}")

    # 6. SOLICITUDES, ASIGNACIONES, SERVICIOS, PAGOS Y CALIFICACIONES (70 solicitudes repartidas)
    print("\n--- Generando Solicitudes completadas y activas por cada cliente ---")

    comentarios_clientes = [
        "Llegó super rápido y solucionó el problema en menos de 15 minutos. Excelente servicio.",
        "Muy profesional el mecánico, tenía todas las herramientas necesarias.",
        "Gran atención, el servicio de grúa fue cuidadoso con el vehículo.",
        "Totalmente recomendado, respondió la llamada de inmediato.",
        "Amable y eficiente. Me salvó la tarde.",
        "Buen servicio de cerrajería, abrió la puerta sin dañar la pintura."
    ]

    comentarios_proveedores = [
        "Cliente puntual y muy amable.",
        "Ubicación precisa facilitó la llegada rápida.",
        "Excelente cliente, pago realizado sin inconvenientes.",
        "Muy buena comunicación por parte del cliente."
    ]

    solicitud_count = 0
    # Create 6 completed, 1 in-progress, 1 pending for each of the 10 clients
    for idx_cli, id_c in enumerate(cliente_ids):
        # find client's vehicle
        cur.execute("SELECT id_vehiculo FROM vehiculo WHERE id_cliente = %s", (id_c,))
        v_rows = cur.fetchall()
        if not v_rows:
            continue
        
        for k in range(7): # 7 solicitudes per client (70 total)
            id_v = v_rows[k % len(v_rows)][0]
            taller_assigned_idx = (idx_cli + k) % 3
            taller_id = taller_ids[taller_assigned_idx]
            
            # Find proveedor of this taller
            cur.execute("SELECT id_proveedor FROM proveedor_servicio WHERE id_taller = %s", (taller_id,))
            prov_rows = cur.fetchall()
            id_p = prov_rows[k % len(prov_rows)][0]

            # Find catalog service for this taller
            cur.execute("SELECT id_catalogo_servicio, precio_estandar, nombre FROM catalogo_servicio WHERE id_taller = %s", (taller_id,))
            cat_rows = cur.fetchall()
            cat_item = cat_rows[k % len(cat_rows)]
            cat_id, cat_precio, cat_nombre = cat_item[0], float(cat_item[1]), cat_item[2]

            zona_id = (k % 5) + 1
            lats = [-17.7833, -17.7200, -17.8600, -17.7800, -17.7800]
            lngs = [-63.1821, -63.1800, -63.1800, -63.1000, -63.2600]
            
            fecha_past = datetime.datetime.now() - datetime.timedelta(days=(idx_cli * 2 + k + 1), hours=k*3)

            if k < 5:
                # COMPLETED SOLICITUD
                cur.execute("""
                    INSERT INTO solicitud (id_vehiculo, id_zona, latitud, longitud, fecha, prioridad, observaciones, descripcion, direccion, estado)
                    VALUES (%s, %s, %s, %s, %s, 'ALTA', %s, %s, 'Santa Cruz de la Sierra', 'completada') RETURNING id_solicitud
                """, (id_v, zona_id, lats[zona_id-1], lngs[zona_id-1], fecha_past, f"Auxilio para {cat_nombre}", f"Solicitud de auxilio por {cat_nombre}"))
                id_sol = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO asignacion (id_solicitud, id_taller, id_proveedor, fecha_inicio, fecha_fin, tiempo_llegada, estado)
                    VALUES (%s, %s, %s, %s, %s, 15.0, 'finalizada') RETURNING id_asignacion
                """, (id_sol, taller_id, id_p, fecha_past, fecha_past + datetime.timedelta(minutes=45)))
                id_asig = cur.fetchone()[0]

                metodo_pago = ["EFECTIVO", "QR", "TARJETA"][k % 3]
                cur.execute("""
                    INSERT INTO pago (monto, fecha, estado, metodo)
                    VALUES (%s, %s, 'completado', %s) RETURNING id_pago
                """, (cat_precio, fecha_past + datetime.timedelta(minutes=40), metodo_pago))
                id_pago = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO servicio (id_asignacion, id_pago, total, fecha_inicio, fecha_fin, estado)
                    VALUES (%s, %s, %s, %s, %s, 'finalizado') RETURNING id_servicio
                """, (id_asig, id_pago, cat_precio, fecha_past, fecha_past + datetime.timedelta(minutes=45)))
                id_serv = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO detalle_servicio (id_servicio, id_catalogo_servicio, cantidad, precio, sub_total, nombre, observacion)
                    VALUES (%s, %s, 1, %s, %s, %s, 'Servicio completado con éxito')
                """, (id_serv, cat_id, cat_precio, cat_precio, cat_nombre))

                # Calificación del cliente al taller
                puntuacion = 5 if k % 2 == 0 else 4
                comentario_taller = comentarios_clientes[k % len(comentarios_clientes)]
                cur.execute("""
                    INSERT INTO calificacion (id_servicio, puntuacion, fecha, comentario)
                    VALUES (%s, %s, %s, %s)
                """, (id_serv, puntuacion, fecha_past + datetime.timedelta(minutes=50), comentario_taller))

                # Calificación del taller/proveedor al cliente
                comentario_cli = comentarios_proveedores[k % len(comentarios_proveedores)]
                cur.execute("""
                    INSERT INTO calificacion_cliente (id_servicio, id_cliente, puntuacion, fecha, comentario)
                    VALUES (%s, %s, 5, %s, %s)
                """, (id_serv, id_c, fecha_past + datetime.timedelta(minutes=50), comentario_cli))

            elif k == 5:
                # EN PROCESO SOLICITUD
                cur.execute("""
                    INSERT INTO solicitud (id_vehiculo, id_zona, latitud, longitud, fecha, prioridad, observaciones, descripcion, direccion, estado)
                    VALUES (%s, %s, %s, %s, NOW(), 'ALTA', %s, %s, 'Santa Cruz de la Sierra', 'en_proceso') RETURNING id_solicitud
                """, (id_v, zona_id, lats[zona_id-1], lngs[zona_id-1], f"Auxilio urgente {cat_nombre}", f"Servicio en curso por {cat_nombre}"))
                id_sol = cur.fetchone()[0]

                cur.execute("""
                    INSERT INTO asignacion (id_solicitud, id_taller, id_proveedor, fecha_inicio, tiempo_llegada, estado)
                    VALUES (%s, %s, %s, NOW(), 10.0, 'en_proceso')
                """, (id_sol, taller_id, id_p))

            else:
                # PENDIENTE SOLICITUD
                cur.execute("""
                    INSERT INTO solicitud (id_vehiculo, id_zona, latitud, longitud, fecha, prioridad, observaciones, descripcion, direccion, estado)
                    VALUES (%s, %s, %s, %s, NOW(), 'MEDIA', %s, %s, 'Santa Cruz de la Sierra', 'pendiente')
                """, (id_v, zona_id, lats[zona_id-1], lngs[zona_id-1], f"Solicitud de auxilio {cat_nombre}", f"Esperando atención por {cat_nombre}"))

            solicitud_count += 1

    conn.commit()
    cur.close()
    conn.close()
    print(f"\n✅ Base de datos poblada exitosamente con {solicitud_count} solicitudes, vehículos, talleres y servicios!")

if __name__ == "__main__":
    seed_database()

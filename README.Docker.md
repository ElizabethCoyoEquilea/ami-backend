# Docker y despliegue en AWS EC2

## Archivos agregados

- `Dockerfile`: construye la imagen del backend FastAPI.
- `.dockerignore`: evita copiar entorno virtual, secretos, logs y uploads.
- `docker-compose.yml`: levanta la API usando la conexion de base de datos definida en `.env`.
- `.env.docker.example`: plantilla segura de variables para Docker.

## Ejecutar localmente con Docker Compose

1. Copia la plantilla:

```bash
cp .env.docker.example .env
```

2. Edita `.env` y cambia al menos:

```env
DB_PASSWORD=una-contrasena-segura
DB_HOST=endpoint-o-ip-de-tu-postgres
DB_PORT=5432
JWT_SECRET_KEY=una-clave-larga-segura
INVITATION_ACCEPT_URL_BASE=http://localhost:8000/auth/talleres/invitaciones/aceptar
```

3. Levanta los servicios:

```bash
docker compose up -d --build
```

4. Verifica:

```bash
curl http://localhost:8000/
```

La respuesta esperada es:

```json
{"message":"API funcionando"}
```

## Despliegue en EC2

1. Crea una instancia EC2 Ubuntu o Amazon Linux.
2. Abre el puerto `8000` en el Security Group, o usa Nginx/ALB para exponer `80`/`443`.
3. Instala Docker y el plugin de Compose.
4. Copia el proyecto a la instancia.
5. Crea el archivo `.env` desde `.env.docker.example` y configura valores reales.
6. Ejecuta:

```bash
docker compose up -d --build
```

7. Revisa logs:

```bash
docker compose logs -f api
```

## Notas de produccion

- No subas `.env` ni archivos JSON de credenciales al repositorio.
- La base de datos no se levanta en Docker Compose; el contenedor usa `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` y `DB_PASSWORD` desde `.env`.
- Si usas Amazon RDS, `DB_HOST` debe ser el endpoint de RDS y el Security Group de RDS debe permitir conexiones desde la EC2.
- Para HTTPS en produccion, coloca Nginx, Caddy, Traefik o un Application Load Balancer delante del contenedor.
- Los archivos subidos quedan en el volumen Docker `uploads_data`.
- La aplicacion crea tablas y ejecuta seeds al iniciar, segun la logica actual de `app/main.py`.

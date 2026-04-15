# ami-backend

Este documento describe, de forma general, la funcion de cada carpeta del proyecto.

## Estructura General

### app/
Carpeta principal de la aplicacion. Contiene toda la logica del backend (configuracion, modelos, rutas, servicios, etc.).

## Estructura Dentro de app/

### core/
Configuraciones centrales de la aplicacion: variables de entorno, conexion a base de datos y seguridad.

### models/
Definicion de entidades/tablas del sistema (estructura de datos persistidos).

### repositories/
Capa de acceso a datos. Se encarga de consultar y persistir informacion en la base de datos.

### routers/
Definicion de endpoints HTTP (rutas de la API) que exponen funcionalidades del sistema.

### schemas/
Esquemas de entrada/salida para validacion y serializacion de datos (contratos de la API).

### services/
Logica de negocio de la aplicacion. Orquesta validaciones, reglas y llamadas a repositorios.

### seeds/
Scripts o utilidades para poblar datos iniciales/requeridos en la base de datos.

### utils/
Funciones auxiliares reutilizables para tareas transversales (por ejemplo envio de correo).

## Archivos Relevantes en la Raiz

### .env
Variables de entorno locales usadas en ejecucion.

### ,env.example
Plantilla de variables de entorno para configurar el proyecto en otros entornos.

### requirements.txt
Listado de dependencias de Python necesarias para ejecutar el backend.

### Comando que deben ejecutar en ese orden para instalar lo necesario para el backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

### Para ejecutar el proyecto
uvicorn app.main:app --reload
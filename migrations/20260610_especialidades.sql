CREATE TABLE IF NOT EXISTS especialidad (
    id_especialidad SERIAL PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE,
    nombre VARCHAR(150) NOT NULL,
    descripcion VARCHAR(500)
);

INSERT INTO especialidad (codigo, nombre, descripcion) VALUES
    ('MANT', 'Mantenimiento', 'Servicios preventivos y correctivos basicos.'),
    ('DIAG', 'Diagnostico', 'Revision y diagnostico tecnico del vehiculo.'),
    ('ELEC', 'Electrico', 'Servicios electricos y bateria.'),
    ('AUX', 'Auxilio vial', 'Atencion de emergencia en ruta.'),
    ('MEC', 'Mecanica', 'Servicios de mecanica general.')
ON CONFLICT (codigo) DO NOTHING;

CREATE TABLE IF NOT EXISTS proveedor_especialidad (
    id_proveedor_especialidad SERIAL PRIMARY KEY,
    id_proveedor INTEGER NOT NULL REFERENCES proveedor_servicio(id_proveedor),
    id_especialidad INTEGER NOT NULL REFERENCES especialidad(id_especialidad),
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_proveedor_especialidad_proveedor_especialidad
        UNIQUE (id_proveedor, id_especialidad)
);

ALTER TABLE proveedor_servicio
    DROP COLUMN IF EXISTS especialidad;

ALTER TABLE catalogo_servicio
    ADD COLUMN IF NOT EXISTS id_especialidad INTEGER;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'catalogo_servicio'
            AND column_name = 'categoria'
    ) THEN
        UPDATE catalogo_servicio
        SET id_especialidad = especialidad.id_especialidad
        FROM especialidad
        WHERE catalogo_servicio.id_especialidad IS NULL
            AND lower(catalogo_servicio.categoria) = lower(especialidad.nombre);
    END IF;
END $$;

ALTER TABLE catalogo_servicio
    DROP COLUMN IF EXISTS categoria,
    DROP COLUMN IF EXISTS unidad_medida;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_catalogo_servicio_especialidad'
    ) THEN
        ALTER TABLE catalogo_servicio
            ADD CONSTRAINT fk_catalogo_servicio_especialidad
                FOREIGN KEY (id_especialidad)
                REFERENCES especialidad(id_especialidad);
    END IF;
END $$;

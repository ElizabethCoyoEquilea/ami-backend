from sqlalchemy import text

from app.core.database import engine


def apply_schema_updates() -> None:
    statements = [
        """
        INSERT INTO especialidad (codigo, nombre, descripcion) VALUES
            ('MECANICA_GENERAL', 'Mecanica general', 'Mecanica general'),
            ('ELECTRICIDAD', 'Electricidad automotriz', 'Electricidad automotriz'),
            ('NEUMATICOS', 'Neumaticos y llantas', 'Neumaticos y llantas'),
            ('FRENOS', 'Sistema de frenos', 'Sistema de frenos'),
            ('MOTOR', 'Motor', 'Motor'),
            ('REFRIGERACION', 'Refrigeracion del motor', 'Refrigeracion del motor'),
            ('SUSPENSION_DIRECCION', 'Suspension y direccion', 'Suspension y direccion'),
            ('TRANSMISION', 'Transmision y embrague', 'Transmision y embrague'),
            ('MANTENIMIENTO', 'Mantenimiento preventivo', 'Mantenimiento preventivo'),
            ('AIRE_ACONDICIONADO', 'Aire acondicionado', 'Aire acondicionado'),
            ('DIAGNOSTICO', 'Diagnostico automotriz', 'Diagnostico automotriz'),
            ('REMOLQUE', 'Grua y traslado', 'Grua y traslado')
        ON CONFLICT (codigo) DO NOTHING
        """,
        """
        ALTER TABLE catalogo_servicio
            ADD COLUMN IF NOT EXISTS id_especialidad INTEGER
        """,
        """
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
        END $$
        """,
        """
        UPDATE catalogo_servicio
        SET id_especialidad = (
            SELECT id_especialidad FROM especialidad WHERE codigo = 'MANTENIMIENTO'
        )
        WHERE id_especialidad IS NULL
        """,
        """
        UPDATE catalogo_servicio c
        SET id_especialidad = e.id_especialidad
        FROM especialidad e
        WHERE e.codigo = CASE
            WHEN lower(c.nombre) LIKE '%aceite%' THEN 'MANTENIMIENTO'
            WHEN lower(c.nombre) LIKE '%diagnostico%' THEN 'DIAGNOSTICO'
            WHEN lower(c.nombre) LIKE '%bateria%' THEN 'ELECTRICIDAD'
            WHEN lower(c.nombre) LIKE '%electrica%' THEN 'ELECTRICIDAD'
            WHEN lower(c.nombre) LIKE '%grua%' THEN 'REMOLQUE'
            WHEN lower(c.nombre) LIKE '%llanta%' THEN 'NEUMATICOS'
            WHEN lower(c.nombre) LIKE '%freno%' THEN 'FRENOS'
            WHEN lower(c.nombre) LIKE '%bujia%' THEN 'MOTOR'
            ELSE NULL
        END
        AND EXISTS (
            SELECT 1
            FROM especialidad actual
            WHERE actual.id_especialidad = c.id_especialidad
                AND actual.codigo IN ('MANT', 'DIAG', 'ELEC', 'AUX', 'MEC')
        )
        """,
        """
        ALTER TABLE catalogo_servicio
            ALTER COLUMN id_especialidad SET NOT NULL
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint c
                JOIN pg_attribute a
                    ON a.attrelid = c.conrelid
                    AND a.attnum = ANY(c.conkey)
                WHERE c.conrelid = 'catalogo_servicio'::regclass
                    AND c.confrelid = 'especialidad'::regclass
                    AND c.contype = 'f'
                    AND a.attname = 'id_especialidad'
            ) THEN
                ALTER TABLE catalogo_servicio
                    ADD CONSTRAINT fk_catalogo_servicio_especialidad
                    FOREIGN KEY (id_especialidad)
                    REFERENCES especialidad(id_especialidad);
            END IF;
        END $$
        """,
        """
        ALTER TABLE catalogo_servicio
            DROP COLUMN IF EXISTS categoria,
            DROP COLUMN IF EXISTS unidad_medida
        """,
        """
        ALTER TABLE proveedor_servicio
            DROP COLUMN IF EXISTS especialidad
        """,
        """
        DELETE FROM especialidad e
        WHERE e.codigo IN ('MANT', 'DIAG', 'ELEC', 'AUX', 'MEC')
            AND NOT EXISTS (
                SELECT 1
                FROM catalogo_servicio c
                WHERE c.id_especialidad = e.id_especialidad
            )
            AND NOT EXISTS (
                SELECT 1
                FROM proveedor_especialidad pe
                WHERE pe.id_especialidad = e.id_especialidad
            )
        """,
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_constraint
                WHERE conname = 'uq_proveedor_especialidad_proveedor_especialidad'
            ) THEN
                ALTER TABLE proveedor_especialidad
                    ADD CONSTRAINT uq_proveedor_especialidad_proveedor_especialidad
                    UNIQUE (id_proveedor, id_especialidad);
            END IF;
        END $$
        """,
    ]

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))

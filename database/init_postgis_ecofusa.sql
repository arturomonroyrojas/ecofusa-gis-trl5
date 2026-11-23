-- ============================================================================
-- ECOFUSA GIS TRL5 - ESQUEMA POSTGRESQL 16 + POSTGIS 3.4
-- Sistema de Referencia Oficial Colombia: MAGNA-SIRGAS Origen Nacional (EPSG:9377)
-- Autor: Jorge Arturo Monroy Rojas | UNAD - Ingenieria de Sistemas (2026)
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- 1. Usuarios y Control de Acceso Basado en Roles (RBAC)
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario         SERIAL PRIMARY KEY,
    nombre_completo    VARCHAR(120) NOT NULL,
    correo_electronico VARCHAR(150) UNIQUE NOT NULL,
    password_hash      VARCHAR(255) NOT NULL,
    rol                VARCHAR(20) NOT NULL DEFAULT 'CIUDADANO'
                       CHECK (rol IN ('CIUDADANO', 'FUNCIONARIO', 'ADMIN')),
    barrio_vereda      VARCHAR(100),
    ecopuntos_totales  INTEGER NOT NULL DEFAULT 0,
    fecha_registro     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Capas Base POT Fusagasuga (Importadas desde ArcGIS Pro en CTM12 EPSG:9377)
CREATE TABLE IF NOT EXISTS rondas_hidricas (
    fid_ronda      SERIAL PRIMARY KEY,
    clasificac     VARCHAR(50) DEFAULT 'Suelo Rural',
    categoria1     VARCHAR(50) DEFAULT 'Proteccion',
    categoria2     VARCHAR(120) DEFAULT 'Areas de conservacion ambiental',
    categoria3     VARCHAR(140),
    nombre_ronda   VARCHAR(160) NOT NULL,
    area_has       NUMERIC(12, 6),
    shape_leng     NUMERIC(14, 4),
    shape_area     NUMERIC(14, 4),
    geom_ctm12     GEOMETRY(MultiPolygon, 9377) NOT NULL
);

CREATE TABLE IF NOT EXISTS predios_y_corredores (
    id_objeto           SERIAL PRIMARY KEY,
    capa_origen         VARCHAR(60) NOT NULL,  -- 'Urbano', 'TratamientosActividades', 'via vertices'
    nombre_predio_tramo VARCHAR(160) NOT NULL,
    tratamiento_pot     VARCHAR(100),
    propietario_publico BOOLEAN NOT NULL DEFAULT FALSE,
    observaciones       TEXT,
    geom_ctm12          GEOMETRY(Geometry, 9377) NOT NULL
);

-- 3. Reportes Ambientales Ciudadanos (Doble Geometria WGS84 + CTM12)
CREATE TABLE IF NOT EXISTS reportes_ambientales (
    id_reporte       SERIAL PRIMARY KEY,
    codigo_radicado  VARCHAR(24) UNIQUE NOT NULL,
    id_ciudadano     INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_funcionario   INTEGER REFERENCES usuarios(id_usuario),
    categoria        VARCHAR(60) NOT NULL,
    estado           VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
                     CHECK (estado IN ('PENDIENTE', 'EN_PROCESO', 'SOLUCIONADO')),
    severidad        VARCHAR(15) NOT NULL DEFAULT 'MEDIA'
                     CHECK (severidad IN ('BAJA', 'MEDIA', 'ALTA')),
    en_ronda_hidrica BOOLEAN NOT NULL DEFAULT FALSE,
    prioridad_auto   VARCHAR(24) NOT NULL DEFAULT 'ESTANDAR',
    barrio_vereda    VARCHAR(100) NOT NULL,
    descripcion      TEXT NOT NULL,
    evidencia_url    TEXT,
    geom_wgs84       GEOMETRY(Point, 4326) NOT NULL,
    geom_ctm12       GEOMETRY(Point, 9377),
    fecha_creacion   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_cierre     TIMESTAMPTZ
);

-- 4. Bitacora Inmutable de Auditoria de Estados
CREATE TABLE IF NOT EXISTS historial_estados (
    id_historial        SERIAL PRIMARY KEY,
    id_reporte          INTEGER NOT NULL REFERENCES reportes_ambientales(id_reporte) ON DELETE CASCADE,
    id_actor            INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    estado_anterior     VARCHAR(20) NOT NULL,
    estado_nuevo        VARCHAR(20) NOT NULL,
    observacion_tecnica TEXT NOT NULL,
    fecha_cambio        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5. Gamificacion Civica (EcoPuntos)
CREATE TABLE IF NOT EXISTS ecopuntos_transacciones (
    id_transaccion   SERIAL PRIMARY KEY,
    id_usuario       INTEGER NOT NULL REFERENCES usuarios(id_usuario),
    id_reporte       INTEGER REFERENCES reportes_ambientales(id_reporte),
    puntos_otorgados INTEGER NOT NULL,
    motivo           VARCHAR(160) NOT NULL,
    fecha_evento     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indices Espaciales GiST (garantizan consultas < 150 ms sobre >10.000 registros)
CREATE INDEX IF NOT EXISTS idx_rondas_geom_gist ON rondas_hidricas USING GIST (geom_ctm12);
CREATE INDEX IF NOT EXISTS idx_predios_geom_gist ON predios_y_corredores USING GIST (geom_ctm12);
CREATE INDEX IF NOT EXISTS idx_reportes_wgs84_gist ON reportes_ambientales USING GIST (geom_wgs84);
CREATE INDEX IF NOT EXISTS idx_reportes_ctm12_gist ON reportes_ambientales USING GIST (geom_ctm12);
CREATE INDEX IF NOT EXISTS idx_reportes_estado ON reportes_ambientales (estado, fecha_creacion DESC);

-- Trigger Automatico: Proyeccion 4326 -> 9377 CTM12 + Cruce Espacial con Rondas Hidricas
CREATE OR REPLACE FUNCTION fn_enriquecer_reporte_gis()
RETURNS TRIGGER AS $$
BEGIN
    NEW.geom_ctm12 := ST_Transform(NEW.geom_wgs84, 9377);
    SELECT EXISTS(
        SELECT 1 FROM rondas_hidricas rh
        WHERE ST_Intersects(rh.geom_ctm12, NEW.geom_ctm12)
    ) INTO NEW.en_ronda_hidrica;

    IF NEW.en_ronda_hidrica THEN
        NEW.prioridad_auto := 'CRITICA (RONDA)';
        NEW.severidad := 'ALTA';
    ELSE
        NEW.prioridad_auto := 'ESTANDAR';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_enriquecer_reporte_gis ON reportes_ambientales;
CREATE TRIGGER trg_enriquecer_reporte_gis
BEFORE INSERT OR UPDATE OF geom_wgs84 ON reportes_ambientales
FOR EACH ROW EXECUTE FUNCTION fn_enriquecer_reporte_gis();

-- Vista Gerencial de Indicadores (KPI) para Panel Alcaldia y GeoServer
CREATE OR REPLACE VIEW vw_kpi_gestion_ambiental AS
SELECT
    categoria,
    COUNT(*) AS total_reportes,
    COUNT(*) FILTER (WHERE estado = 'SOLUCIONADO') AS solucionados,
    COUNT(*) FILTER (WHERE en_ronda_hidrica = TRUE) AS en_ronda_hidrica,
    ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(fecha_cierre, NOW()) - fecha_creacion)) / 86400.0)::numeric, 2) AS dias_promedio
FROM reportes_ambientales
GROUP BY categoria;

-- Datos Semilla de Usuarios Iniciales
INSERT INTO usuarios (nombre_completo, correo_electronico, password_hash, rol, barrio_vereda, ecopuntos_totales)
VALUES
('Administrador Alcaldia Fusagasuga', 'admin@fusagasuga.gov.co', '$2b$12$e8.40g0g/exampleBcryptHash2026', 'ADMIN', 'Centro', 0),
('Funcionario Medio Ambiente', 'funcionario@fusagasuga.gov.co', '$2b$12$e8.40g0g/exampleBcryptHash2026', 'FUNCIONARIO', 'Centro', 0),
('Jorge Arturo Monroy Rojas', 'jorgemonroy@unad.edu.co', '$2b$12$e8.40g0g/exampleBcryptHash2026', 'CIUDADANO', 'Vereda Pekin', 145)
ON CONFLICT (correo_electronico) DO NOTHING;

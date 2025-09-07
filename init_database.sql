-- Crear database (ejecutar como superuser)
-- CREATE DATABASE seccionadora_logs;

-- Conectar a la database seccionadora_logs antes de ejecutar lo siguiente

-- Tabla principal de registros de cortes
CREATE TABLE IF NOT EXISTS cortes_seccionadora (
    id SERIAL PRIMARY KEY,
    nombre_optimizacion VARCHAR(255) NOT NULL,
    job_key VARCHAR(255) NOT NULL,
    fecha_proceso DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    largo_mm DECIMAL(10,3) NOT NULL,
    ancho_mm DECIMAL(10,3) NOT NULL,
    espesor_mm DECIMAL(10,3) NOT NULL,
    cantidad_placas INTEGER NOT NULL,
    fecha_carga TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Columnas calculadas para analytics
    duracion_segundos INTEGER GENERATED ALWAYS AS (
        EXTRACT(EPOCH FROM (hora_fin - hora_inicio))
    ) STORED,
    
    area_mm2 DECIMAL(15,3) GENERATED ALWAYS AS (
        largo_mm * ancho_mm
    ) STORED,
    
    volumen_mm3 DECIMAL(18,3) GENERATED ALWAYS AS (
        largo_mm * ancho_mm * espesor_mm
    ) STORED
);

-- Índices para optimizar consultas de analytics
CREATE INDEX IF NOT EXISTS idx_cortes_fecha_proceso ON cortes_seccionadora(fecha_proceso);
CREATE INDEX IF NOT EXISTS idx_cortes_job_key ON cortes_seccionadora(job_key);
CREATE INDEX IF NOT EXISTS idx_cortes_fecha_carga ON cortes_seccionadora(fecha_carga);
CREATE INDEX IF NOT EXISTS idx_cortes_espesor ON cortes_seccionadora(espesor_mm);

-- Vista para métricas diarias
CREATE OR REPLACE VIEW metricas_diarias AS
SELECT 
    fecha_proceso,
    COUNT(*) as total_cortes,
    COUNT(DISTINCT job_key) as jobs_unicos,
    SUM(cantidad_placas) as total_placas,
    AVG(duracion_segundos) as duracion_promedio_seg,
    SUM(duracion_segundos) as tiempo_total_seg,
    AVG(area_mm2) as area_promedio_mm2,
    SUM(area_mm2 * cantidad_placas) as area_total_mm2,
    AVG(espesor_mm) as espesor_promedio_mm,
    MIN(espesor_mm) as espesor_min_mm,
    MAX(espesor_mm) as espesor_max_mm
FROM cortes_seccionadora
GROUP BY fecha_proceso
ORDER BY fecha_proceso;

-- Vista para análisis por job
CREATE OR REPLACE VIEW analisis_por_job AS
SELECT 
    job_key,
    COUNT(*) as total_cortes,
    SUM(cantidad_placas) as total_placas,
    MIN(fecha_proceso) as primera_fecha,
    MAX(fecha_proceso) as ultima_fecha,
    AVG(duracion_segundos) as duracion_promedio_seg,
    SUM(duracion_segundos) as tiempo_total_seg,
    largo_mm,
    ancho_mm,
    espesor_mm,
    area_mm2,
    volumen_mm3
FROM cortes_seccionadora
GROUP BY job_key, largo_mm, ancho_mm, espesor_mm, area_mm2, volumen_mm3
ORDER BY total_placas DESC;

-- Vista para eficiencia por espesores
CREATE OR REPLACE VIEW eficiencia_por_espesor AS
SELECT 
    espesor_mm,
    COUNT(*) as total_cortes,
    SUM(cantidad_placas) as total_placas,
    AVG(duracion_segundos) as duracion_promedio_seg,
    AVG(area_mm2) as area_promedio_mm2,
    COUNT(DISTINCT job_key) as jobs_unicos
FROM cortes_seccionadora
GROUP BY espesor_mm
ORDER BY espesor_mm;
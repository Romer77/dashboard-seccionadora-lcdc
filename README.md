# Dashboard Seccionadora - LCDC Mendoza

## 📋 Descripción General

Sistema integral de análisis y monitoreo para máquina seccionadora de MDF que permite visualizar métricas de producción, eficiencia operativa y tiempo ocioso en tiempo real. La aplicación procesa logs de máquina y presenta dashboards interactivos para toma de decisiones basada en datos.

## 🎯 Funcionalidades Principales

### 📈 Overview General de Producción
- **KPIs Principales**: Total esquemas ejecutados, placas procesadas, placas blancas 18mm, promedio placas/día
- **KPIs de Eficiencia**: Promedio minutos/esquema, horas máquina, placas por hora, porcentaje tiempo ocioso
- **Tendencias Diarias**: Gráficos temporales de esquemas, placas, horas máquina y eficiencia
- **Análisis Temporal**: Visualización de tiempo ocioso y su impacto en la productividad
- **Distribución por Espesores**: Análisis comparativo de materiales procesados

### 📅 Análisis Diario de Producción
- **Filtros Temporales**: Selección de rangos de fechas personalizados
- **Métricas del Período**: Resúmenes estadísticos del período seleccionado
- **Evolución Temporal**: 6 gráficos simultáneos (esquemas, placas, horas máquina, eficiencia, tiempo ocioso, placas 18mm)
- **Análisis de Correlaciones**: Relaciones entre horas máquina vs eficiencia y tiempo ocioso vs productividad
- **Tabla Detallada**: Datos granulares por día con métricas calculadas

### ⚡ Análisis por Espesores
- **Resumen por Material**: Estadísticas de espesores más utilizados y eficientes
- **Comparación Visual**: Gráficos de distribución y tiempos promedio
- **Análisis de Eficiencia**: Scatter plot relacionando duración vs volumen de producción
- **Insights Automáticos**: Identificación de materiales más y menos eficientes
- **Tabla Detallada**: Métricas por espesor incluyendo placas/esquema y área procesada

### 🔧 Análisis por Jobs
- **Filtros Dinámicos**: Top N jobs ordenables por diferentes criterios
- **Visualizaciones Comparativas**: Gráficos de barras horizontales para top jobs
- **Análisis de Distribución**: Scatter plots y histogramas de rendimiento
- **Análisis Dimensional**: Relación área de corte vs duración y distribución por espesor
- **Insights de Rendimiento**: Identificación automática de jobs más eficientes y productivos

## 🏗️ Arquitectura Técnica

### Stack Tecnológico
```
Frontend: Streamlit (Python)
Backend: PostgreSQL
Visualización: Plotly Express/Graph Objects
ETL: Pandas + SQLAlchemy
Deployment: Streamlit Community Cloud
```

### Arquitectura de Datos

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Log Files     │    │     ETL      │    │   PostgreSQL    │
│   (.txt)        │───▶│  Processing  │───▶│   Database      │
│                 │    │              │    │                 │
└─────────────────┘    └──────────────┘    └─────────────────┘
                              │                       │
                              ▼                       ▼
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐
│   Processed     │    │  Data Cache  │    │   Streamlit     │
│   Archive       │    │  (5 min TTL) │    │   Dashboard     │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

### Base de Datos

#### Tabla Principal: `cortes_seccionadora`
```sql
- id: SERIAL PRIMARY KEY
- nombre_optimizacion: VARCHAR(255) -- Nombre del archivo de esquema
- job_key: VARCHAR(255) -- Identificador único del trabajo
- fecha_proceso: DATE -- Fecha de procesamiento
- hora_inicio/hora_fin: TIME -- Timestamps de ejecución
- largo_mm, ancho_mm, espesor_mm: DECIMAL -- Dimensiones
- cantidad_placas: INTEGER -- Placas procesadas en el esquema
- duracion_segundos: INTEGER (CALCULATED) -- Duración automática
- area_mm2, volumen_mm3: DECIMAL (CALCULATED) -- Métricas calculadas
```

#### Vistas Analíticas Preconstruidas
- **`metricas_diarias`**: Agregaciones por fecha con KPIs diarios
- **`analisis_por_job`**: Métricas agrupadas por trabajo único
- **`eficiencia_por_espesor`**: Estadísticas por tipo de material

### Componentes del Sistema

#### 1. ETL Pipeline (`etl_secc.py`)
```python
def main():
    # 1. Procesar archivos de log nuevos
    # 2. Transformar datos para PostgreSQL
    # 3. Cargar a base de datos
    # 4. Archivar archivos procesados
```

#### 2. Parser de Logs (`script_seccionadora.py`)
```python
def procesar_archivo(filepath):
    # Parsea líneas del formato:
    # LOG=ruta,largo,ancho,espesor,min,hora,seg,mes,año,día,hora_fin,min_fin,seg_fin,placas
    # Extrae job_key preciso eliminando extensión
    # Convierte a DataFrame estructurado
```

#### 3. Dashboard Principal (`dashboard_streamlit.py`)
- **Conexión**: SQLAlchemy con cache de 5 minutos
- **Consultas**: SQL optimizado con CTEs y window functions
- **Visualización**: Plotly con múltiples tipos de gráficos
- **Interactividad**: Filtros, selección de períodos, navegación

## 🔄 Flujo de Trabajo

### 1. Ingesta de Datos
```
Logs de Máquina (.txt) → Carpeta archivos_entrada/
```

### 2. Procesamiento ETL
```bash
python etl_secc.py
```
- Lee archivos de `archivos_entrada/`
- Parsea logs con `script_seccionadora.py`
- Transforma datos (fecha, hora, dimensiones)
- Inserta en PostgreSQL
- Mueve archivos a `procesados/` con timestamp

### 3. Visualización
```bash
streamlit run dashboard_streamlit.py
```
- Conecta a PostgreSQL
- Cache de consultas (5 min TTL)
- Renderiza dashboards interactivos
- Actualización automática de datos

### 4. Deployment
```
GitHub → Streamlit Community Cloud → Producción
```

## 📊 Métricas y KPIs Clave

### KPIs Operativos
- **Total Esquemas**: Número de trabajos ejecutados
- **Placas Procesadas**: Volumen total de producción
- **Placas Blancas 18mm**: Métrica específica de material principal
- **Promedio Placas/Día**: Capacidad diaria promedio

### KPIs de Eficiencia
- **Promedio Min/Esquema**: Tiempo promedio por trabajo
- **Horas Máquina**: Tiempo productivo real
- **Placas por Hora**: Throughput de producción
- **Tiempo Ocioso %**: Eficiencia temporal de la máquina

### Cálculo de Tiempo Ocioso
```sql
tiempo_span = MAX(hora_fin) - MIN(hora_inicio)  -- Tiempo total del día
tiempo_productivo = SUM(duracion_segundos)       -- Tiempo trabajando
tiempo_ocioso = tiempo_span - tiempo_productivo  -- Tiempo muerto
porcentaje_ocioso = (tiempo_ocioso / tiempo_span) * 100
```

## 🛠️ Configuración y Deploy

### Requisitos del Sistema
```
Python 3.8+
PostgreSQL 12+
Dependencias: requirements.txt
```

### Variables de Entorno
```env
PG_CONN=postgresql://user:password@host:port/seccionadora_logs
```

### Deployment en Streamlit Cloud
1. **Preparación**: Subir código a GitHub (público)
2. **Conexión**: Vincular repositorio en share.streamlit.io
3. **Configuración**: Agregar `PG_CONN` en secrets
4. **Deploy**: Automático en cada push a main

### Estructura de Archivos
```
Seccionadora/
├── dashboard_streamlit.py      # Dashboard principal
├── etl_secc.py                # Pipeline ETL
├── script_seccionadora.py     # Parser de logs
├── init_database.sql          # Schema de BD
├── requirements.txt           # Dependencias
├── .streamlit/config.toml     # Configuración UI
├── README.md                  # Esta documentación
├── README_DEPLOYMENT.md       # Guía de deployment
├── .env.example              # Plantilla de variables
├── archivos_entrada/         # Logs nuevos
└── procesados/              # Logs archivados
```

## 🔒 Consideraciones de Seguridad

- **Variables de Entorno**: Credenciales no hardcodeadas
- **SSL**: Conexiones encriptadas automáticas
- **Cache**: TTL de 5 minutos para datos sensibles
- **Logs**: Sin exposición de información confidencial

## 🚀 Mejoras Futuras

### Funcionalidades
- [ ] Alertas automáticas por baja eficiencia
- [ ] Predicción de mantenimiento
- [ ] Reportes PDF automatizados
- [ ] API REST para integración

### Técnico
- [ ] Migración a base de datos en la nube
- [ ] Implementación de CI/CD
- [ ] Tests automatizados
- [ ] Monitoreo de aplicación

## 📞 Soporte

Para problemas técnicos:
1. Verificar logs en Streamlit Cloud dashboard
2. Validar conexión a PostgreSQL
3. Revisar formato de archivos de log
4. Contactar al desarrollador para soporte especializado

---

**Desarrollado para LCDC Mendoza - Sistema de Análisis de Seccionadora MDF**
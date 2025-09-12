import streamlit as st

# DEBUG Y TEST DE CONEXIÓN DIRECTA
st.write("🔍 **DEBUG Y TEST DE CONEXIÓN:**")
st.write(f"Streamlit version: {st.__version__}")

# Importar módulo de database simplificado
try:
    from database import get_database_connection, create_db_engine, DATABASE_URL
    import socket
    import sqlalchemy
    
    st.write("✅ Módulo database importado correctamente")
    
    # Test conexión directa
    db_url = get_database_connection()
    if db_url:
        st.write(f"✅ DATABASE_URL obtenida: {db_url[:50]}...")
        
        # Test de conectividad de red
        st.write("🌐 **Test de conectividad:**")
        try:
            # Extraer host de la conexión
            host = "db.cyjracwepjzzeygfpbxr.supabase.co"
            port = 5432
            
            # Test básico de socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                st.success("✅ Puerto 5432 alcanzable")
            else:
                st.error(f"❌ Puerto 5432 no alcanzable (código: {result})")
                
        except Exception as e:
            st.error(f"❌ Error de conectividad: {e}")
        
        # Test con parámetros SSL
        st.write("🔒 **Test con SSL:**")
        try:
            # Conexión con SSL requerido
            ssl_url = DATABASE_URL + "?sslmode=require"
            engine_ssl = sqlalchemy.create_engine(ssl_url, connect_args={"connect_timeout": 10})
            
            with engine_ssl.connect() as conn:
                result = conn.execute(sqlalchemy.text("SELECT version()")).fetchone()
            st.success(f"✅ Conexión SSL exitosa: {result[0][:50]}...")
            
        except Exception as e:
            st.error(f"❌ Error SSL: {e}")
        
        # Test engine original
        engine = create_db_engine()
        if engine:
            st.write("✅ Engine creado y testeado exitosamente")
        else:
            st.write("❌ Error creando engine")
    else:
        st.write("❌ No se pudo obtener DATABASE_URL")
        
except Exception as e:
    st.error(f"❌ Error importando database module: {e}")

st.write("---")

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import create_engine, text
from datetime import datetime, timedelta
import logging
from typing import Optional

# Importar conexión de base de datos simplificada
from database import DATABASE_URL, ENGINE

# Verificación inicial
if not DATABASE_URL or not ENGINE:
    st.error("❌ Configuración de base de datos fallida")
    st.stop()

# Configurar logging básico
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seccionadora_dashboard")

# Configurar página con configuración básica
st.set_page_config(
    page_title="Dashboard Seccionadora - LCDC",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Paleta de colores corporativa LCDC
COLORS = {
    'primary': '#2E86AB',      # Azul corporativo
    'secondary': '#A23B72',    # Magenta corporativo  
    'accent': '#F18F01',       # Naranja vibrante
    'success': '#C73E1D',      # Rojo corporativo
    'info': '#85C1E9',         # Azul claro
    'warning': '#F7B801',      # Amarillo/dorado
    'light': '#F8F9FA',        # Gris muy claro
    'dark': '#2C3E50',         # Gris oscuro
}

def create_kpi_explanation(kpi_name: str, explanation: str):
    """Crear elemento desplegable explicativo para KPIs"""
    with st.expander(f"ℹ️ ¿Qué significa {kpi_name}?"):
        st.info(explanation)

def format_time_duration(seconds: float) -> str:
    """Formatear duración en formato legible"""
    if pd.isna(seconds) or seconds == 0:
        return "0h 0min"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}min"

def get_connection():
    """Obtener conexión a PostgreSQL usando ENGINE global"""
    return ENGINE

@st.cache_data(ttl=300)  # 5 minutos
def load_data(query: str) -> pd.DataFrame:
    """Cargar datos desde PostgreSQL con manejo de errores robusto"""
    logger.debug(f"Ejecutando consulta: {query[:100]}...")
    
    try:
        engine = get_connection()
        if engine is None:
            return pd.DataFrame()
            
        df = pd.read_sql(query, engine)
        logger.info(f"Consulta exitosa - Filas: {len(df)}")
        return df
        
    except Exception as e:
        logger.error(f"Error ejecutando consulta: {e}")
        st.error(f"❌ Error en consulta de datos: {e}")
        
        # Mostrar información de ayuda según el tipo de error
        if "relation" in str(e).lower():
            st.info("💡 Parece que falta crear las tablas en la base de datos")
        elif "authentication" in str(e).lower():
            st.info("💡 Error de autenticación - verifica usuario y contraseña")
        elif "connection" in str(e).lower():
            st.info("💡 Error de conexión - verifica host y puerto")
            
        return pd.DataFrame()

def main():
    """Función principal de la aplicación"""
    
    # Header con información del sistema
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🏭 Dashboard Seccionadora - LCDC Mendoza")
    with col2:
        st.caption("Entorno: STREAMLIT_CLOUD")
        if st.button("🔄 Limpiar Cache", help="Limpiar cache de datos"):
            st.cache_data.clear()
            st.success("Cache limpiado exitosamente")
            
    st.markdown("---")
    
    # Configuración ya validada al inicio del archivo
    # La conexión ENGINE ya fue testeada en database.py
        
    # Validar conexión a base de datos solo al cargar datos
    # No bloquear la carga inicial de la interfaz
    
    # Sidebar para navegación
    st.sidebar.title("📊 Navegación")
    page = st.sidebar.selectbox(
        "Seleccionar vista:",
        ["📈 Análisis de Producción", "⚡ Análisis por Espesores", "🔧 Análisis por Jobs"]
    )
    
    if page == "📈 Análisis de Producción":
        show_production_analysis()
    elif page == "⚡ Análisis por Espesores":
        show_thickness_analysis()
    elif page == "🔧 Análisis por Jobs":
        show_jobs_analysis()

def show_production_analysis():
    st.header("📈 Análisis de Producción")
    
    # Filtro de fechas en sidebar
    with st.sidebar:
        st.markdown("### 📅 Filtros de Fecha")
        fecha_inicio = st.date_input("Fecha inicio", value=datetime(2025, 7, 1), key="production_start")
        fecha_fin = st.date_input("Fecha fin", value=datetime(2025, 8, 13), key="production_end")
    
    # ==================== SECCIÓN 1: KPIs EJECUTIVOS ====================
    st.subheader("📊 Indicadores Ejecutivos del Período")
    
    # KPIs principales corregidos según lógica de negocio LCDC
    col1, col2, col3, col4 = st.columns(4)
    
    # Consultar datos principales corregidos con filtro de fecha
    total_data = load_data(f"""
        SELECT 
            COUNT(*) as total_esquemas,
            SUM(cantidad_placas) as total_placas_procesadas,
            COUNT(DISTINCT job_key) as jobs_unicos,
            COUNT(DISTINCT fecha_proceso) as dias_activos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(CASE WHEN espesor_mm = 18 THEN cantidad_placas ELSE 0 END) as placas_blancas_18mm
        FROM cortes_seccionadora
        WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
    """)
    
    # Calcular métricas de tiempo corregidas según indicaciones con filtro de fecha
    tiempo_data = load_data(f"""
        WITH daily_machine_time AS (
            SELECT 
                fecha_proceso,
                MIN(hora_inicio) as primer_inicio,
                MAX(hora_fin) as ultimo_fin,
                EXTRACT(EPOCH FROM (MAX(hora_fin) - MIN(hora_inicio))) as tiempo_total_maquina_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY fecha_proceso
        ),
        daily_productive_time AS (
            SELECT 
                fecha_proceso,
                SUM(duracion_segundos) as tiempo_productivo_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY fecha_proceso
        )
        SELECT 
            SUM(dt.tiempo_total_maquina_seg) as tiempo_total_maquina_segundos,
            SUM(dp.tiempo_productivo_seg) as tiempo_total_productivo_segundos,
            CASE WHEN SUM(dt.tiempo_total_maquina_seg) > 0 
                 THEN (SUM(dp.tiempo_productivo_seg) / SUM(dt.tiempo_total_maquina_seg)) * 100 
                 ELSE 0 
            END as tasa_tiempo_productivo,
            CASE WHEN SUM(dt.tiempo_total_maquina_seg) > 0 
                 THEN ((SUM(dt.tiempo_total_maquina_seg) - SUM(dp.tiempo_productivo_seg)) / SUM(dt.tiempo_total_maquina_seg)) * 100 
                 ELSE 0 
            END as tasa_tiempo_improductivo
        FROM daily_machine_time dt
        JOIN daily_productive_time dp ON dt.fecha_proceso = dp.fecha_proceso
    """)
    
    if not total_data.empty and not tiempo_data.empty:
        data = total_data.iloc[0]
        tiempo = tiempo_data.iloc[0]
        
        with col1:
            st.metric(
                "🔧 Total Esquemas",
                f"{int(data['total_esquemas']):,}",
                help="Esquemas de trabajo ejecutados"
            )
            create_kpi_explanation(
                "Total Esquemas",
                "Cada esquema representa un programa de corte específico. Un esquema puede procesar una o varias placas según el diseño."
            )
        
        with col2:
            st.metric(
                "📦 Placas Procesadas",
                f"{int(data['total_placas_procesadas']):,}",
                help="Total de placas de MDF procesadas"
            )
        
        with col3:
            st.metric(
                "⚪ Placas Blancas 18mm",
                f"{int(data['placas_blancas_18mm']):,}",
                help="Placas de MDF blanco de 18mm"
            )
        
        with col4:
            promedio_placas_dia = data['total_placas_procesadas'] / data['dias_activos']
            st.metric(
                "📊 Promedio Placas/Día",
                f"{promedio_placas_dia:.1f}",
                help="Capacidad diaria promedio"
            )
    
    # Segunda fila de KPIs corregidos
    col1, col2, col3, col4 = st.columns(4)
    
    if not total_data.empty and not tiempo_data.empty:
        with col1:
            promedio_min_esquema = data['duracion_promedio_seg'] / 60
            st.metric(
                "⏱️ Min/Esquema",
                f"{promedio_min_esquema:.1f} min",
                help="Tiempo promedio por esquema"
            )
            create_kpi_explanation(
                "Minutos por Esquema",
                "Tiempo promedio que tarda la máquina en ejecutar cada esquema de corte. Incluye tiempo de corte y preparación."
            )
        
        with col2:
            horas_maquina_total = tiempo['tiempo_total_maquina_segundos'] / 3600
            st.metric(
                "🕐 Tiempo Total Máquina",
                f"{format_time_duration(tiempo['tiempo_total_maquina_segundos'])}",
                help="Tiempo total desde primer a último trabajo"
            )
            create_kpi_explanation(
                "Tiempo Total Máquina",
                "Tiempo total desde que inicia el primer trabajo del día hasta que termina el último. Incluye tiempo productivo + tiempos muertos."
            )
        
        with col3:
            horas_productivo = tiempo['tiempo_total_productivo_segundos'] / 3600
            st.metric(
                "⚡ Tiempo Productivo",
                f"{format_time_duration(tiempo['tiempo_total_productivo_segundos'])}",
                help="Tiempo real trabajando (sin tiempos muertos)"
            )
            create_kpi_explanation(
                "Tiempo Productivo",
                "Tiempo que la máquina estuvo realmente cortando placas. No incluye paradas, preparación entre trabajos o tiempos muertos."
            )
        
        with col4:
            st.metric(
                "📈 Tasa Productividad",
                f"{tiempo['tasa_tiempo_productivo']:.1f}%",
                help="Porcentaje del tiempo que la máquina estuvo produciendo"
            )
            create_kpi_explanation(
                "Tasa de Productividad",
                "Porcentaje del tiempo total que la máquina estuvo realmente trabajando. Una tasa alta indica mayor eficiencia operativa."
            )
    
    # Tercera fila de KPIs adicionales
    col1, col2, col3, col4 = st.columns(4)
    
    if not total_data.empty and not tiempo_data.empty:
        with col1:
            st.metric(
                "📉 Tasa Improductiva",
                f"{tiempo['tasa_tiempo_improductivo']:.1f}%",
                help="Porcentaje de tiempo muerto o inactivo"
            )
            create_kpi_explanation(
                "Tasa Improductiva",
                "Porcentaje del tiempo total en que la máquina no estaba produciendo. Incluye cambios de herramientas, esperas, y paradas."
            )
            
        with col2:
            placas_por_hora = data['total_placas_procesadas'] / (tiempo['tiempo_total_productivo_segundos'] / 3600)
            st.metric(
                "🚀 Placas/Hora Efectiva",
                f"{placas_por_hora:.1f}",
                help="Placas procesadas por hora de tiempo productivo"
            )
            create_kpi_explanation(
                "Placas por Hora Efectiva",
                "Número de placas procesadas por cada hora de tiempo productivo real. Mide la eficiencia pura de la máquina cuando está trabajando."
            )
            
        with col3:
            dias_activos = data['dias_activos']
            st.metric(
                "📅 Días Activos",
                f"{int(dias_activos)}",
                help="Días con producción registrada"
            )
            create_kpi_explanation(
                "Días Activos",
                "Cantidad de días en el período con actividad registrada en la máquina. Útil para analizar la utilización del equipo."
            )
            
        with col4:
            jobs_unicos = data['jobs_unicos']
            st.metric(
                "🔧 Trabajos Diferentes",
                f"{int(jobs_unicos)}",
                help="Cantidad de trabajos únicos procesados"
            )
            create_kpi_explanation(
                "Trabajos Diferentes",
                "Cantidad de diseños o tipos de trabajo diferentes procesados. Indica la variedad de la producción."
            )
    
    st.markdown("---")
    
    # ==================== SECCIÓN 2: ANÁLISIS POR MATERIAL ====================
    st.subheader("📏 Análisis por Tipos de Material (Espesores)")
    create_kpi_explanation(
        "Análisis por Espesores",
        "Comparación del rendimiento de la máquina según el tipo de material (espesor). Permite identificar qué materiales son más eficientes de procesar."
    )
    
    thickness_data = load_data(f"""
        SELECT 
            espesor_mm,
            COUNT(*) as total_esquemas,
            SUM(cantidad_placas) as total_placas,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(cantidad_placas) / COUNT(*) as promedio_placas_por_esquema
        FROM cortes_seccionadora
        WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        GROUP BY espesor_mm
        ORDER BY total_placas DESC
    """)
    
    if not thickness_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Crear paleta personalizada para el pie chart
            colors_pie = [COLORS['primary'], COLORS['accent'], COLORS['secondary'], 
                         COLORS['info'], COLORS['warning'], COLORS['success'], COLORS['dark']]
            
            fig_pie = px.pie(
                thickness_data, 
                values='total_placas', 
                names='espesor_mm',
                title='📊 Distribución de Placas por Tipo de Material',
                color_discrete_sequence=colors_pie
            )
            fig_pie.update_traces(
                textposition='inside', 
                textinfo='percent+label',
                hovertemplate='<b>Espesor: %{label} mm</b><br>' +
                             'Placas: %{value}<br>' +
                             'Porcentaje: %{percent}<extra></extra>'
            )
            fig_pie.update_layout(
                height=400,
                title_font_size=14,
                title_x=0.5
            )
            st.plotly_chart(fig_pie, use_container_width=True)
        
        with col2:
            thickness_data['duracion_min'] = thickness_data['duracion_promedio_seg'] / 60
            fig_bar = px.bar(
                thickness_data, 
                x='espesor_mm', 
                y='duracion_min',
                title='⏱️ Tiempo Promedio por Esquema según Material',
                labels={'espesor_mm': 'Espesor del Material (mm)', 'duracion_min': 'Tiempo Promedio (minutos)'},
                color='duracion_min',
                color_continuous_scale=[[0, COLORS['info']], [1, COLORS['success']]])
            fig_bar.update_traces(
                hovertemplate='<b>Espesor: %{x} mm</b><br>' +
                             'Tiempo promedio: %{y:.1f} min<extra></extra>'
            )
            fig_bar.update_layout(
                height=400,
                title_font_size=14,
                title_x=0.5,
                xaxis_title="Espesor del Material (mm)",
                yaxis_title="Tiempo Promedio (minutos)",
                coloraxis_showscale=False
            )
            st.plotly_chart(fig_bar, use_container_width=True)
    
    st.markdown("---")
    
    # ==================== SECCIÓN 3: ANÁLISIS DE RELACIONES ====================
    st.subheader("🔍 Análisis de Relaciones Entre Indicadores")
    create_kpi_explanation(
        "Análisis de Relaciones",
        "Gráficos de dispersión que muestran cómo se relacionan diferentes indicadores entre sí. Ayudan a identificar patrones y correlaciones para optimizar la operación."
    )
    
    # Datos diarios para análisis de relaciones
    daily_data = load_data(f"""
        WITH daily_analysis AS (
            SELECT 
                fecha_proceso,
                COUNT(*) as total_esquemas,
                SUM(cantidad_placas) as total_placas,
                COUNT(DISTINCT job_key) as jobs_unicos,
                AVG(duracion_segundos) as duracion_promedio_seg,
                SUM(duracion_segundos) as tiempo_total_seg,
                MIN(hora_inicio) as primer_inicio,
                MAX(hora_fin) as ultimo_fin,
                SUM(CASE WHEN espesor_mm = 18 THEN cantidad_placas ELSE 0 END) as placas_18mm
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY fecha_proceso
        ),
        daily_with_ocioso AS (
            SELECT 
                *,
                EXTRACT(EPOCH FROM (ultimo_fin - primer_inicio)) / 3600.0 as tiempo_span_horas,
                tiempo_total_seg / 3600.0 as tiempo_productivo_horas,
                (EXTRACT(EPOCH FROM (ultimo_fin - primer_inicio)) - tiempo_total_seg) / 3600.0 as tiempo_ocioso_horas
            FROM daily_analysis
        )
        SELECT 
            fecha_proceso,
            total_esquemas,
            total_placas,
            placas_18mm,
            jobs_unicos,
            duracion_promedio_seg,
            tiempo_productivo_horas,
            tiempo_ocioso_horas,
            tiempo_span_horas,
            CASE WHEN tiempo_span_horas > 0 
                 THEN (tiempo_ocioso_horas / tiempo_span_horas) * 100 
                 ELSE 0 
            END as porcentaje_ocioso,
            CASE WHEN tiempo_span_horas > 0 
                 THEN (tiempo_productivo_horas / tiempo_span_horas) * 100 
                 ELSE 0 
            END as tasa_productiva,
            total_placas / tiempo_productivo_horas as placas_por_hora
        FROM daily_with_ocioso
        ORDER BY fecha_proceso
    """)
    
    if not daily_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            fig_scatter = px.scatter(
                daily_data, 
                x='tiempo_productivo_horas', 
                y='placas_por_hora',
                size='total_placas', 
                color='tasa_productiva',
                title='🔄 Relación: Tiempo Productivo vs Eficiencia',
                labels={
                    'tiempo_productivo_horas': 'Horas Productivas', 
                    'placas_por_hora': 'Placas/Hora',
                    'tasa_productiva': 'Tasa Productiva (%)',
                    'total_placas': 'Total Placas'
                },
                color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]],
                hover_data=['fecha_proceso', 'total_esquemas']
            )
            fig_scatter.update_traces(
                hovertemplate='<b>%{customdata[0]}</b><br>' +
                             'Horas Productivas: %{x:.1f}h<br>' +
                             'Placas/Hora: %{y:.1f}<br>' +
                             'Total Placas: %{marker.size}<br>' +
                             'Esquemas: %{customdata[1]}<extra></extra>'
            )
            fig_scatter.update_layout(height=400)
            st.plotly_chart(fig_scatter, use_container_width=True)
            create_kpi_explanation(
                "Tiempo Productivo vs Eficiencia",
                "Relación entre las horas de trabajo efectivo y la eficiencia (placas/hora). El tamaño indica volumen total. Ayuda a identificar si días con más horas productivas son proporcionalmente más eficientes."
            )
        
        with col2:
            fig_ocioso = px.scatter(
                daily_data, 
                x='porcentaje_ocioso', 
                y='placas_por_hora',
                size='total_placas', 
                color='total_esquemas',
                title='📉 Impacto del Tiempo Improductivo en la Eficiencia',
                labels={
                    'porcentaje_ocioso': 'Tiempo Improductivo (%)', 
                    'placas_por_hora': 'Placas/Hora',
                    'total_esquemas': 'Esquemas',
                    'total_placas': 'Total Placas'
                },
                color_continuous_scale=[[0, COLORS['success']], [1, COLORS['secondary']]],
                hover_data=['fecha_proceso']
            )
            fig_ocioso.update_traces(
                hovertemplate='<b>%{customdata[0]}</b><br>' +
                             'Tiempo Improductivo: %{x:.1f}%<br>' +
                             'Placas/Hora: %{y:.1f}<br>' +
                             'Total Placas: %{marker.size}<br>' +
                             'Esquemas: %{marker.color}<extra></extra>'
            )
            fig_ocioso.update_layout(height=400)
            st.plotly_chart(fig_ocioso, use_container_width=True)
            create_kpi_explanation(
                "Impacto del Tiempo Improductivo",
                "Cómo afecta el porcentaje de tiempo improductivo a la eficiencia general. Puntos hacia la izquierda (menos tiempo improductivo) deberían mostrar mayor eficiencia."
            )
    
    st.markdown("---")
    
    # ==================== SECCIÓN 4: DETALLES OPERATIVOS ====================
    st.subheader("📋 Registros Detallados por Esquema")
    create_kpi_explanation(
        "Registros Detallados",
        "Tabla completa con todos los esquemas procesados en el período seleccionado, incluyendo el tiempo muerto calculado entre cada registro."
    )
    
    # Cargar datos completos de registros con tiempo muerto calculado
    if not daily_data.empty:
        detailed_data = load_data(f"""
            WITH registros_ordenados AS (
                SELECT 
                    *,
                    ROW_NUMBER() OVER (PARTITION BY fecha_proceso ORDER BY hora_inicio) as orden_dia
                FROM cortes_seccionadora
                WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            ),
            con_siguiente AS (
                SELECT 
                    r1.*,
                    r2.hora_inicio as siguiente_inicio
                FROM registros_ordenados r1
                LEFT JOIN registros_ordenados r2 ON r1.fecha_proceso = r2.fecha_proceso 
                                                   AND r1.orden_dia = r2.orden_dia - 1
            )
            SELECT 
                fecha_proceso,
                hora_inicio,
                hora_fin, 
                job_key,
                cantidad_placas,
                espesor_mm,
                duracion_segundos,
                CASE 
                    WHEN siguiente_inicio IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (siguiente_inicio - hora_fin))
                    ELSE 0 
                END as tiempo_muerto_segundos,
                CASE 
                    WHEN siguiente_inicio IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (siguiente_inicio - hora_fin)) / 60.0
                    ELSE 0 
                END as tiempo_muerto_minutos
            FROM con_siguiente
            ORDER BY fecha_proceso, hora_inicio
        """)
        
        if not detailed_data.empty:
            # Preparar datos para mostrar
            display_data = detailed_data.copy()
            display_data['duracion_min'] = (display_data['duracion_segundos'] / 60).round(1)
            display_data['tiempo_muerto_min'] = display_data['tiempo_muerto_minutos'].round(1)
            display_data['hora_inicio'] = display_data['hora_inicio'].astype(str)
            display_data['hora_fin'] = display_data['hora_fin'].astype(str)
            display_data['fecha_proceso'] = pd.to_datetime(display_data['fecha_proceso']).dt.strftime('%d/%m/%Y')
            
            # Seleccionar columnas para mostrar
            display_cols = [
                'fecha_proceso', 'hora_inicio', 'hora_fin', 'job_key', 
                'cantidad_placas', 'espesor_mm', 'duracion_min', 'tiempo_muerto_min'
            ]
            
            col_names = {
                'fecha_proceso': 'Fecha',
                'hora_inicio': 'Inicio', 
                'hora_fin': 'Fin',
                'job_key': 'Trabajo',
                'cantidad_placas': 'Placas',
                'espesor_mm': 'Espesor (mm)',
                'duracion_min': 'Duración (min)',
                'tiempo_muerto_min': 'Tiempo Muerto (min)'
            }
            
            display_data_renamed = display_data[display_cols].rename(columns=col_names)
            
            # Mostrar tabla con paginación
            st.dataframe(
                display_data_renamed,
                use_container_width=True,
                height=400
            )
            
            # Estadísticas de la tabla
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Registros", len(detailed_data))
            with col2:
                tiempo_muerto_total = detailed_data['tiempo_muerto_minutos'].sum()
                st.metric("Tiempo Muerto Total", f"{tiempo_muerto_total:.0f} min")
            with col3:
                tiempo_muerto_promedio = detailed_data['tiempo_muerto_minutos'].mean()
                st.metric("Tiempo Muerto Promedio", f"{tiempo_muerto_promedio:.1f} min")
            with col4:
                registros_con_tiempo_muerto = (detailed_data['tiempo_muerto_minutos'] > 0).sum()
                st.metric("Registros con Tiempo Muerto", registros_con_tiempo_muerto)
        else:
            st.info("No hay registros detallados para mostrar en el período seleccionado")
    else:
        st.warning("No hay datos para el período seleccionado")

def show_thickness_analysis():
    st.header("⚡ Análisis por Espesores de Material")
    create_kpi_explanation(
        "Análisis por Espesores",
        "Comparación detallada del rendimiento de la máquina según el tipo de material procesado. Cada espesor tiene características diferentes que afectan los tiempos de corte y la eficiencia."
    )
    
    # Datos por espesor
    thickness_data = load_data("SELECT * FROM eficiencia_por_espesor ORDER BY espesor_mm")
    
    if not thickness_data.empty:
        # Métricas generales
        st.subheader("📊 Resumen por Material")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Espesores Diferentes", f"{len(thickness_data)}")
        with col2:
            most_used = thickness_data.loc[thickness_data['total_placas'].idxmax(), 'espesor_mm']
            st.metric("Espesor Más Usado", f"{most_used} mm")
        with col3:
            fastest = thickness_data.loc[thickness_data['duracion_promedio_seg'].idxmin(), 'espesor_mm']
            st.metric("Esquemas Más Rápidos", f"{fastest} mm")
        
        # Gráficos comparativos
        col1, col2 = st.columns(2)
        
        with col1:
            fig_volume = px.bar(thickness_data, x='espesor_mm', y='total_placas',
                               title='📊 Total de Placas por Espesor',
                               labels={'espesor_mm': 'Espesor (mm)', 'total_placas': 'Total Placas'},
                               color='total_placas',
                               color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_volume.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_volume, use_container_width=True)
            create_kpi_explanation(
                "Total de Placas por Espesor",
                "Muestra la cantidad total de placas procesadas para cada tipo de material. Los materiales más utilizados aparecen con barras más altas."
            )
        
        with col2:
            fig_efficiency = px.bar(thickness_data, x='espesor_mm', y='duracion_promedio_seg',
                                   title='⏱️ Duración Promedio por Espesor',
                                   labels={'espesor_mm': 'Espesor (mm)', 'duracion_promedio_seg': 'Segundos'},
                                   color='duracion_promedio_seg',
                                   color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_efficiency.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_efficiency, use_container_width=True)
            create_kpi_explanation(
                "Duración Promedio por Espesor",
                "Tiempo promedio que tarda cada esquema según el tipo de material. Materiales más gruesos o duros típicamente requieren más tiempo."
            )
        
        # Análisis de eficiencia
        st.subheader("🔍 Análisis de Eficiencia")
        
        # Calcular métricas adicionales
        thickness_data['placas_por_esquema'] = thickness_data['total_placas'] / thickness_data['total_cortes']
        thickness_data['duracion_min'] = thickness_data['duracion_promedio_seg'] / 60
        thickness_data['area_m2'] = thickness_data['area_promedio_mm2'] / 1_000_000
        
        fig_scatter = px.scatter(thickness_data, 
                                x='duracion_promedio_seg', 
                                y='total_placas',
                                size='area_promedio_mm2',
                                color='espesor_mm',
                                title='🔍 Relación Duración vs Volumen de Producción',
                                labels={'duracion_promedio_seg': 'Duración Promedio (seg)', 
                                       'total_placas': 'Total Placas Producidas'},
                                hover_data=['espesor_mm', 'total_cortes'],
                                color_continuous_scale=[[0, COLORS['info']], [1, COLORS['accent']]])
        st.plotly_chart(fig_scatter, use_container_width=True)
        create_kpi_explanation(
            "Relación Duración vs Volumen",
            "Gráfico de dispersión que relaciona el tiempo promedio de procesamiento con el volumen total producido. El tamaño de los puntos representa el área promedio. Ayuda a identificar materiales eficientes vs voluminosos."
        )
        
        # Tabla detallada
        st.subheader("📋 Detalle por Espesor")
        
        display_thickness = thickness_data.copy()
        display_thickness = display_thickness.round(2)
        display_thickness['area_m2'] = display_thickness['area_m2'].round(4)
        
        display_cols = ['espesor_mm', 'total_cortes', 'total_placas', 'jobs_unicos', 
                       'duracion_min', 'placas_por_esquema', 'area_m2']
        
        col_names = {'espesor_mm': 'Espesor (mm)', 'total_cortes': 'Total Esquemas',
                    'total_placas': 'Total Placas', 'jobs_unicos': 'Jobs Únicos',
                    'duracion_min': 'Duración Prom (min)', 'placas_por_esquema': 'Placas/Esquema',
                    'area_m2': 'Área Prom (m²)'}
        
        display_thickness_renamed = display_thickness[display_cols].rename(columns=col_names)
        st.dataframe(display_thickness_renamed, use_container_width=True)
        
        # Recomendaciones
        st.subheader("💡 Insights y Recomendaciones")
        
        most_efficient = thickness_data.loc[thickness_data['duracion_promedio_seg'].idxmin()]
        least_efficient = thickness_data.loc[thickness_data['duracion_promedio_seg'].idxmax()]
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"""
            **Más Eficiente: {most_efficient['espesor_mm']} mm**
            - Duración promedio: {most_efficient['duracion_promedio_seg']/60:.1f} min
            - Total producido: {most_efficient['total_placas']} placas
            """)
        
        with col2:
            st.warning(f"""
            **Menos Eficiente: {least_efficient['espesor_mm']} mm**
            - Duración promedio: {least_efficient['duracion_promedio_seg']/60:.1f} min
            - Total producido: {least_efficient['total_placas']} placas
            """)
    else:
        st.warning("No hay datos de espesores disponibles")

def show_jobs_analysis():
    st.header("🔧 Análisis por Jobs")
    create_kpi_explanation(
        "Análisis por Jobs",
        "Análisis detallado de cada tipo de trabajo procesado en la máquina. Cada 'job' representa un diseño o tipo de corte específico que puede repetirse en múltiples esquemas."
    )
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        top_n = st.selectbox("Mostrar top:", [10, 20, 50, 100], index=1)
    with col2:
        sort_by = st.selectbox("Ordenar por:", 
                              ["Total Placas", "Total Esquemas", "Tiempo Total", "Duración Promedio"],
                              index=0)
    
    # Mapeo de opciones a columnas
    sort_mapping = {
        "Total Placas": "total_placas",
        "Total Esquemas": "total_cortes", 
        "Tiempo Total": "tiempo_total_seg",
        "Duración Promedio": "duracion_promedio_seg"
    }
    
    # Datos por job
    jobs_data = load_data(f"""
        SELECT * FROM analisis_por_job 
        ORDER BY {sort_mapping[sort_by]} DESC 
        LIMIT {top_n}
    """)
    
    if not jobs_data.empty:
        # Métricas generales
        st.subheader("📊 Resumen de Jobs")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Jobs Mostrados", f"{len(jobs_data)}")
        with col2:
            st.metric("Placas Totales", f"{jobs_data['total_placas'].sum():,}")
        with col3:
            st.metric("Promedio Placas/Job", f"{jobs_data['total_placas'].mean():.1f}")
        with col4:
            total_hours = jobs_data['tiempo_total_seg'].sum() / 3600
            st.metric("Tiempo Total", f"{total_hours:.1f}h")
        
        # Gráfico de top jobs
        st.subheader(f"📈 Top {top_n} Jobs por {sort_by}")
        create_kpi_explanation(
            f"Top {sort_by}",
            "Comparación de los jobs más importantes según el criterio seleccionado. Permite identificar qué tipos de trabajo son más frecuentes o demandantes."
        )
        
        # Truncar nombres largos para mejor visualización
        jobs_data['job_key_short'] = jobs_data['job_key'].str[-30:]  # Últimos 30 caracteres
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_top_jobs = px.bar(jobs_data.head(15), 
                                 x='total_placas', 
                                 y='job_key_short',
                                 orientation='h',
                                 title=f'📆 Top 15 Jobs por Total de Placas',
                                 labels={'total_placas': 'Total Placas', 'job_key_short': 'Job'},
                                 color='total_placas',
                                 color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_top_jobs.update_layout(height=600, coloraxis_showscale=False)
            st.plotly_chart(fig_top_jobs, use_container_width=True)
            create_kpi_explanation(
                "Top Jobs por Placas",
                "Los 15 tipos de trabajo que más placas han procesado. Identifica los diseños más demandados por los clientes."
            )
        
        with col2:
            fig_duration = px.bar(jobs_data.head(15), 
                                 x='duracion_promedio_seg', 
                                 y='job_key_short',
                                 orientation='h',
                                 title='⏱️ Duración Promedio por Corte (seg)',
                                 labels={'duracion_promedio_seg': 'Duración Promedio (seg)', 'job_key_short': 'Job'},
                                 color='duracion_promedio_seg',
                                 color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_duration.update_layout(height=600, coloraxis_showscale=False)
            st.plotly_chart(fig_duration, use_container_width=True)
            create_kpi_explanation(
                "Duración Promedio por Corte",
                "Tiempo promedio que tarda cada esquema de estos jobs. Jobs con mayor duración pueden requerir más planificación o ser más complejos."
            )
        
        # Análisis de distribución
        st.subheader("🔍 Análisis de Distribución")
        create_kpi_explanation(
            "Análisis de Distribución",
            "Gráficos que muestran patrones y relaciones entre diferentes características de los jobs. Ayudan a entender la variabilidad y distribución de los trabajos."
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_scatter = px.scatter(jobs_data, 
                                    x='total_cortes', 
                                    y='total_placas',
                                    size='tiempo_total_seg',
                                    color='espesor_mm',
                                    title='📊 Relación Esquemas vs Placas por Job',
                                    labels={'total_cortes': 'Total Esquemas', 'total_placas': 'Total Placas'},
                                    hover_data=['job_key', 'duracion_promedio_seg'],
                                    color_continuous_scale=[[0, COLORS['info']], [1, COLORS['accent']]])
            st.plotly_chart(fig_scatter, use_container_width=True)
            create_kpi_explanation(
                "Esquemas vs Placas",
                "Muestra cuántos esquemas se necesitaron para producir las placas de cada job. El tamaño del punto indica tiempo total. Jobs eficientes procesan muchas placas con pocos esquemas."
            )
        
        with col2:
            # Histograma de duración promedio
            fig_hist = px.histogram(jobs_data, 
                                   x='duracion_promedio_seg',
                                   nbins=20,
                                   title='📈 Distribución de Duración Promedio',
                                   labels={'duracion_promedio_seg': 'Duración Promedio (seg)', 'count': 'Cantidad de Jobs'},
                                   color_discrete_sequence=[COLORS['primary']])
            st.plotly_chart(fig_hist, use_container_width=True)
            create_kpi_explanation(
                "Distribución de Duración",
                "Histograma que muestra cómo se distribuyen los tiempos de procesamiento. La mayoría de jobs deberían agruparse en rangos similares para operación eficiente."
            )
        
        # Análisis por dimensiones
        st.subheader("📏 Análisis por Dimensiones")
        create_kpi_explanation(
            "Análisis por Dimensiones",
            "Relación entre el tamaño físico de las piezas y los tiempos de procesamiento. Permite identificar si piezas más grandes o de ciertos espesores requieren tiempos diferentes."
        )
        
        # Calcular área y volumen unitario
        jobs_data['area_mm2'] = jobs_data['largo_mm'] * jobs_data['ancho_mm']
        jobs_data['volumen_mm3'] = jobs_data['area_mm2'] * jobs_data['espesor_mm']
        jobs_data['area_m2'] = jobs_data['area_mm2'] / 1_000_000
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Scatter por área
            fig_area = px.scatter(jobs_data, 
                                 x='area_m2', 
                                 y='duracion_promedio_seg',
                                 size='total_placas',
                                 color='espesor_mm',
                                 title='📐 Duración vs Área de Corte',
                                 labels={'area_m2': 'Área (m²)', 'duracion_promedio_seg': 'Duración (seg)'},
                                 hover_data=['job_key', 'largo_mm', 'ancho_mm'],
                                 color_continuous_scale=[[0, COLORS['info']], [1, COLORS['accent']]])
            st.plotly_chart(fig_area, use_container_width=True)
            create_kpi_explanation(
                "Duración vs Área",
                "Relación entre el área de las piezas y el tiempo de procesamiento. El tamaño de los puntos indica volumen total producido. Ayuda a entender si piezas más grandes tardan proporcionalmente más tiempo."
            )
        
        with col2:
            # Box plot por espesor
            fig_box = px.box(jobs_data, 
                            x='espesor_mm', 
                            y='duracion_promedio_seg',
                            title='📦 Distribución de Duración por Espesor',
                            labels={'espesor_mm': 'Espesor (mm)', 'duracion_promedio_seg': 'Duración (seg)'},
                            color_discrete_sequence=[COLORS['primary']])
            st.plotly_chart(fig_box, use_container_width=True)
            create_kpi_explanation(
                "Distribución por Espesor",
                "Diagrama de caja que muestra la variabilidad de tiempos para cada espesor. Las cajas muestran el rango típico, líneas indican valores extremos. Ayuda a identificar espesores con mayor variabilidad."
            )
        
        # Tabla detallada
        st.subheader("📋 Detalle de Jobs")
        
        # Preparar datos para mostrar
        display_jobs = jobs_data.copy()
        display_jobs['duracion_min'] = (display_jobs['duracion_promedio_seg'] / 60).round(1)
        display_jobs['tiempo_total_min'] = (display_jobs['tiempo_total_seg'] / 60).round(1)
        display_jobs['area_m2'] = display_jobs['area_m2'].round(4)
        display_jobs['primera_fecha'] = pd.to_datetime(display_jobs['primera_fecha']).dt.strftime('%d/%m/%Y')
        display_jobs['ultima_fecha'] = pd.to_datetime(display_jobs['ultima_fecha']).dt.strftime('%d/%m/%Y')
        
        display_cols = ['job_key', 'total_cortes', 'total_placas', 'primera_fecha', 'ultima_fecha',
                       'duracion_min', 'tiempo_total_min', 'largo_mm', 'ancho_mm', 'espesor_mm', 'area_m2']
        
        col_names = {
            'job_key': 'Job Key',
            'total_cortes': 'Esquemas',
            'total_placas': 'Placas', 
            'primera_fecha': 'Primera Fecha',
            'ultima_fecha': 'Última Fecha',
            'duracion_min': 'Duración Prom (min)',
            'tiempo_total_min': 'Tiempo Total (min)',
            'largo_mm': 'Largo (mm)',
            'ancho_mm': 'Ancho (mm)',
            'espesor_mm': 'Espesor (mm)',
            'area_m2': 'Área (m²)'
        }
        
        display_jobs_renamed = display_jobs[display_cols].rename(columns=col_names)
        st.dataframe(display_jobs_renamed, use_container_width=True)
        
        # Insights
        st.subheader("💡 Insights de Rendimiento")
        
        # Jobs más eficientes y menos eficientes
        most_efficient = jobs_data.loc[jobs_data['duracion_promedio_seg'].idxmin()]
        least_efficient = jobs_data.loc[jobs_data['duracion_promedio_seg'].idxmax()]
        most_productive = jobs_data.loc[jobs_data['total_placas'].idxmax()]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.success(f"""
            **Job Más Eficiente:**
            
            {most_efficient['job_key'][-40:]}
            
            - Duración: {most_efficient['duracion_promedio_seg']/60:.1f} min
            - Total placas: {most_efficient['total_placas']}
            - Espesor: {most_efficient['espesor_mm']} mm
            """)
        
        with col2:
            st.info(f"""
            **Job Más Productivo:**
            
            {most_productive['job_key'][-40:]}
            
            - Total placas: {most_productive['total_placas']}
            - Esquemas: {most_productive['total_cortes']}
            - Tiempo total: {most_productive['tiempo_total_seg']/3600:.1f}h
            """)
        
        with col3:
            st.warning(f"""
            **Job Menos Eficiente:**
            
            {least_efficient['job_key'][-40:]}
            
            - Duración: {least_efficient['duracion_promedio_seg']/60:.1f} min
            - Total placas: {least_efficient['total_placas']}
            - Espesor: {least_efficient['espesor_mm']} mm
            """)
    
    else:
        st.warning("No hay datos de jobs disponibles")

if __name__ == "__main__":
    main()
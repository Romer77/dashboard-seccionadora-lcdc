import streamlit as st

# CONFIGURAR PÁGINA PRIMERO (debe ser lo primero siempre)
st.set_page_config(
    page_title="Dashboard Seccionadora - LCDC",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import con manejo de error
try:
    from database import DATABASE_URL, ENGINE
    
    if ENGINE is None:
        st.error("❌ No se pudo conectar a la base de datos")
        st.info("Verifica la configuración de secrets")
        st.stop()
        
except ImportError as e:
    st.error(f"❌ Error importando database module: {e}")
    st.stop()
except Exception as e:
    st.error(f"❌ Error de configuración: {e}")
    st.stop()

# IMPORTS PARA EL DASHBOARD
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from sqlalchemy import text
from datetime import datetime, timedelta
import logging
from typing import Optional

# Configurar logging básico
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seccionadora_dashboard")

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
    
    # Calcular métricas de tiempo
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
            END as tasa_tiempo_productivo
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
        
        # Segunda fila de KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            promedio_min_esquema = data['duracion_promedio_seg'] / 60
            st.metric(
                "⏱️ Min/Esquema",
                f"{promedio_min_esquema:.1f} min",
                help="Tiempo promedio por esquema"
            )
        
        with col2:
            st.metric(
                "🕐 Tiempo Total Máquina",
                f"{format_time_duration(tiempo['tiempo_total_maquina_segundos'])}",
                help="Tiempo total desde primer a último trabajo"
            )
        
        with col3:
            st.metric(
                "⚡ Tiempo Productivo",
                f"{format_time_duration(tiempo['tiempo_total_productivo_segundos'])}",
                help="Tiempo real trabajando (sin tiempos muertos)"
            )
        
        with col4:
            st.metric(
                "📈 Tasa Productividad",
                f"{tiempo['tasa_tiempo_productivo']:.1f}%",
                help="Porcentaje del tiempo que la máquina estuvo produciendo"
            )
            
        # ==================== SECCIÓN 2: ANÁLISIS POR MATERIAL ====================
        st.markdown("---")
        st.subheader("📏 Análisis por Tipos de Material (Espesores)")
        
        thickness_summary = load_data(f"""
            SELECT 
                espesor_mm,
                COUNT(*) as total_esquemas,
                SUM(cantidad_placas) as total_placas,
                AVG(duracion_segundos) as duracion_promedio_seg
            FROM cortes_seccionadora
            WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
            GROUP BY espesor_mm
            ORDER BY total_placas DESC
        """)
        
        if not thickness_summary.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                # Pie chart de distribución
                fig_pie = px.pie(
                    thickness_summary, 
                    values='total_placas', 
                    names='espesor_mm',
                    title='📊 Distribución de Placas por Espesor',
                    color_discrete_sequence=[COLORS['primary'], COLORS['accent'], COLORS['secondary'], COLORS['info']]
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(height=400, title_font_size=14, title_x=0.5)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col2:
                # Bar chart de tiempos
                thickness_summary['duracion_min'] = thickness_summary['duracion_promedio_seg'] / 60
                fig_bar = px.bar(
                    thickness_summary, 
                    x='espesor_mm', 
                    y='duracion_min',
                    title='⏱️ Tiempo Promedio por Esquema según Espesor',
                    labels={'espesor_mm': 'Espesor (mm)', 'duracion_min': 'Tiempo Promedio (min)'},
                    color='duracion_min',
                    color_continuous_scale=[[0, COLORS['info']], [1, COLORS['success']]]
                )
                fig_bar.update_layout(height=400, title_font_size=14, title_x=0.5, coloraxis_showscale=False)
                st.plotly_chart(fig_bar, use_container_width=True)
        
        # ==================== SECCIÓN 3: ANÁLISIS DE RELACIONES ====================
        st.markdown("---")
        st.subheader("🔍 Análisis de Relaciones Entre Indicadores")
        
        # Datos diarios para análisis
        daily_data = load_data(f"""
            WITH daily_analysis AS (
                SELECT 
                    fecha_proceso,
                    COUNT(*) as total_esquemas,
                    SUM(cantidad_placas) as total_placas,
                    AVG(duracion_segundos) as duracion_promedio_seg,
                    SUM(duracion_segundos) / 3600.0 as tiempo_productivo_horas
                FROM cortes_seccionadora
                WHERE fecha_proceso BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
                GROUP BY fecha_proceso
            )
            SELECT 
                *,
                total_placas / tiempo_productivo_horas as placas_por_hora
            FROM daily_analysis
            ORDER BY fecha_proceso
        """)
        
        if not daily_data.empty and len(daily_data) > 1:
            col1, col2 = st.columns(2)
            
            with col1:
                # Scatter plot tiempo vs eficiencia
                fig_scatter1 = px.scatter(
                    daily_data, 
                    x='tiempo_productivo_horas', 
                    y='placas_por_hora',
                    size='total_placas',
                    title='🔄 Tiempo Productivo vs Eficiencia',
                    labels={
                        'tiempo_productivo_horas': 'Horas Productivas', 
                        'placas_por_hora': 'Placas/Hora',
                        'total_placas': 'Total Placas'
                    },
                    color_discrete_sequence=[COLORS['primary']],
                    hover_data=['fecha_proceso', 'total_esquemas']
                )
                fig_scatter1.update_layout(height=400)
                st.plotly_chart(fig_scatter1, use_container_width=True)
            
            with col2:
                # Scatter plot esquemas vs placas
                fig_scatter2 = px.scatter(
                    daily_data,
                    x='total_esquemas',
                    y='total_placas',
                    size='tiempo_productivo_horas',
                    title='📊 Esquemas vs Placas Procesadas',
                    labels={
                        'total_esquemas': 'Total Esquemas',
                        'total_placas': 'Total Placas',
                        'tiempo_productivo_horas': 'Horas Productivas'
                    },
                    color_discrete_sequence=[COLORS['secondary']],
                    hover_data=['fecha_proceso']
                )
                fig_scatter2.update_layout(height=400)
                st.plotly_chart(fig_scatter2, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos para el período seleccionado")

def show_thickness_analysis():
    st.header("⚡ Análisis por Espesores de Material")
    create_kpi_explanation(
        "Análisis por Espesores",
        "Comparación detallada del rendimiento de la máquina según el tipo de material procesado. Cada espesor tiene características diferentes que afectan los tiempos de corte y la eficiencia."
    )
    
    # Datos por espesor usando tabla agregada
    thickness_data = load_data("""
        SELECT 
            espesor_mm,
            COUNT(*) as total_cortes,
            SUM(cantidad_placas) as total_placas,
            COUNT(DISTINCT job_key) as jobs_unicos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            AVG(largo_mm * ancho_mm) as area_promedio_mm2
        FROM cortes_seccionadora 
        GROUP BY espesor_mm 
        ORDER BY espesor_mm
    """)
    
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
        
        with col2:
            fig_efficiency = px.bar(thickness_data, x='espesor_mm', y='duracion_promedio_seg',
                                   title='⏱️ Duración Promedio por Espesor',
                                   labels={'espesor_mm': 'Espesor (mm)', 'duracion_promedio_seg': 'Segundos'},
                                   color='duracion_promedio_seg',
                                   color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_efficiency.update_layout(coloraxis_showscale=False)
            st.plotly_chart(fig_efficiency, use_container_width=True)
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
        SELECT 
            job_key,
            COUNT(*) as total_cortes,
            SUM(cantidad_placas) as total_placas,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(duracion_segundos) as tiempo_total_seg,
            MIN(fecha_proceso) as primera_fecha,
            MAX(fecha_proceso) as ultima_fecha,
            AVG(largo_mm) as largo_mm,
            AVG(ancho_mm) as ancho_mm,
            AVG(espesor_mm) as espesor_mm
        FROM cortes_seccionadora 
        GROUP BY job_key 
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
        st.subheader(f"📈 Top {min(15, len(jobs_data))} Jobs por {sort_by}")
        
        # Truncar nombres largos para mejor visualización
        display_jobs = jobs_data.head(15).copy()
        display_jobs['job_key_short'] = display_jobs['job_key'].str[-30:]
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_top_jobs = px.bar(display_jobs, 
                                 x='total_placas', 
                                 y='job_key_short',
                                 orientation='h',
                                 title=f'📆 Top Jobs por Total de Placas',
                                 labels={'total_placas': 'Total Placas', 'job_key_short': 'Job'},
                                 color='total_placas',
                                 color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_top_jobs.update_layout(height=600, coloraxis_showscale=False)
            st.plotly_chart(fig_top_jobs, use_container_width=True)
        
        with col2:
            fig_duration = px.bar(display_jobs, 
                                 x='duracion_promedio_seg', 
                                 y='job_key_short',
                                 orientation='h',
                                 title='⏱️ Duración Promedio por Corte (seg)',
                                 labels={'duracion_promedio_seg': 'Duración Promedio (seg)', 'job_key_short': 'Job'},
                                 color='duracion_promedio_seg',
                                 color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_duration.update_layout(height=600, coloraxis_showscale=False)
            st.plotly_chart(fig_duration, use_container_width=True)
    
    else:
        st.warning("No hay datos de jobs disponibles")

# EJECUTAR EL DASHBOARD
main()
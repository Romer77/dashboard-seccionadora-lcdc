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
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2E86AB 0%, #A23B72 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🔧 Total Esquemas</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Programas ejecutados</p>
                </div>
                """.format(int(data['total_esquemas'])), unsafe_allow_html=True)
            create_kpi_explanation(
                "Total Esquemas",
                "Cada esquema representa un programa de corte específico. Un esquema puede procesar una o varias placas según el diseño."
            )
        
        with col2:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #F18F01 0%, #C73E1D 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📦 Placas Procesadas</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Total MDF procesado</p>
                </div>
                """.format(int(data['total_placas_procesadas'])), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #85C1E9 0%, #2E86AB 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">⚪ Placas Blancas 18mm</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Material específico</p>
                </div>
                """.format(int(data['placas_blancas_18mm'])), unsafe_allow_html=True)
        
        with col4:
            promedio_placas_dia = data['total_placas_procesadas'] / data['dias_activos']
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #F7B801 0%, #F18F01 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📊 Promedio Placas/Día</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Capacidad diaria</p>
                </div>
                """.format(promedio_placas_dia), unsafe_allow_html=True)
        
        # Segunda fila de KPIs
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            promedio_min_esquema = data['duracion_promedio_seg'] / 60
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2C3E50 0%, #2E86AB 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">⏱️ Min/Esquema</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">min promedio</p>
                </div>
                """.format(promedio_min_esquema), unsafe_allow_html=True)
        
        with col2:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #A23B72 0%, #C73E1D 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🕐 Tiempo Total</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Span completo</p>
                </div>
                """.format(format_time_duration(tiempo['tiempo_total_maquina_segundos'])), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #F18F01 0%, #F7B801 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">⚡ Tiempo Productivo</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Solo trabajando</p>
                </div>
                """.format(format_time_duration(tiempo['tiempo_total_productivo_segundos'])), unsafe_allow_html=True)
        
        with col4:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #85C1E9 0%, #A23B72 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📈 Productividad</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Eficiencia</p>
                </div>
                """.format(tiempo['tasa_tiempo_productivo']), unsafe_allow_html=True)
        
        # Tercera fila de KPIs avanzados
        st.markdown("### 📊 Métricas Avanzadas")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            tasa_improductiva = 100 - tiempo['tasa_tiempo_productivo']
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #C73E1D 0%, #A23B72 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📉 Tiempo Improductivo</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}%</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Paradas/Esperas</p>
                </div>
                """.format(tasa_improductiva), unsafe_allow_html=True)
        
        with col2:
            placas_por_hora_efectiva = data['total_placas_procesadas'] / (tiempo['tiempo_total_productivo_segundos'] / 3600) if tiempo['tiempo_total_productivo_segundos'] > 0 else 0
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #2E86AB 0%, #85C1E9 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🚀 Placas/Hora Efectiva</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Ritmo productivo</p>
                </div>
                """.format(placas_por_hora_efectiva), unsafe_allow_html=True)
        
        with col3:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #F7B801 0%, #F18F01 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">📅 Días Activos</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Con producción</p>
                </div>
                """.format(int(data['dias_activos'])), unsafe_allow_html=True)
        
        with col4:
            with st.container():
                st.markdown("""
                <div style="background: linear-gradient(90deg, #A23B72 0%, #2C3E50 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                    <h3 style="margin: 0; font-size: 1.2rem;">🔧 Jobs Únicos</h3>
                    <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                    <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Tipos diferentes</p>
                </div>
                """.format(int(data['jobs_unicos'])), unsafe_allow_html=True)
            
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
                fig_pie.update_layout(
                    height=400, 
                    title_font_size=16, 
                    title_x=0.5,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
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
                fig_bar.update_layout(
                    height=400, 
                    title_font_size=16, 
                    title_x=0.5, 
                    title_y=0.95,
                    coloraxis_showscale=False,
                    font=dict(family="Arial, sans-serif", size=12)
                )
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
                fig_scatter1.update_layout(
                    height=400,
                    title_font_size=16,
                    title_x=0.5,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
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
                fig_scatter2.update_layout(
                    height=400,
                    title_font_size=16,
                    title_x=0.5,
                    title_y=0.95,
                    font=dict(family="Arial, sans-serif", size=12)
                )
                st.plotly_chart(fig_scatter2, use_container_width=True)
    else:
        st.warning("⚠️ No hay datos para el período seleccionado")

def show_thickness_analysis():
    st.header("⚡ Análisis por Espesores de Material")
    create_kpi_explanation(
        "Análisis por Espesores",
        "Comparación detallada del rendimiento de la máquina según el tipo de material procesado. Cada espesor tiene características diferentes que afectan los tiempos de corte y la eficiencia."
    )
    
    # Datos por espesor con métricas ampliadas
    thickness_data = load_data("""
        SELECT 
            espesor_mm,
            COUNT(*) as total_cortes,
            SUM(cantidad_placas) as total_placas,
            COUNT(DISTINCT job_key) as jobs_unicos,
            AVG(duracion_segundos) as duracion_promedio_seg,
            SUM(duracion_segundos) as tiempo_total_seg,
            AVG(largo_mm * ancho_mm) as area_promedio_mm2,
            MIN(duracion_segundos) as duracion_min_seg,
            MAX(duracion_segundos) as duracion_max_seg,
            COUNT(DISTINCT fecha_proceso) as dias_procesados,
            AVG(largo_mm) as largo_promedio_mm,
            AVG(ancho_mm) as ancho_promedio_mm
        FROM cortes_seccionadora 
        GROUP BY espesor_mm 
        ORDER BY espesor_mm
    """)
    
    if not thickness_data.empty:
        # ==================== SECCIÓN 1: KPIs POR ESPESOR ====================
        st.subheader("📊 KPIs por Tipo de Material")
        
        # Primera fila de KPIs
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #2E86AB 0%, #A23B72 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">📏 Tipos de Material</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Espesores diferentes</p>
            </div>
            """.format(len(thickness_data)), unsafe_allow_html=True)
        
        with col2:
            most_used = thickness_data.loc[thickness_data['total_placas'].idxmax(), 'espesor_mm']
            most_used_placas = thickness_data.loc[thickness_data['total_placas'].idxmax(), 'total_placas']
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F18F01 0%, #C73E1D 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🏆 Material Principal</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:,} placas</p>
            </div>
            """.format(int(most_used), int(most_used_placas)), unsafe_allow_html=True)
        
        with col3:
            fastest = thickness_data.loc[thickness_data['duracion_promedio_seg'].idxmin(), 'espesor_mm']
            fastest_time = thickness_data.loc[thickness_data['duracion_promedio_seg'].idxmin(), 'duracion_promedio_seg'] / 60
            st.markdown("""
            <div style="background: linear-gradient(90deg, #85C1E9 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">⚡ Más Rápido</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:.1f} min promedio</p>
            </div>
            """.format(int(fastest), fastest_time), unsafe_allow_html=True)
        
        with col4:
            total_tiempo_horas = thickness_data['tiempo_total_seg'].sum() / 3600
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F7B801 0%, #F18F01 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">⏱️ Tiempo Total</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}h</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Todos los materiales</p>
            </div>
            """.format(total_tiempo_horas), unsafe_allow_html=True)
        
        # Segunda fila de KPIs avanzados
        col1, col2, col3, col4 = st.columns(4)
        
        # Calcular métricas adicionales
        thickness_data['placas_por_corte'] = thickness_data['total_placas'] / thickness_data['total_cortes']
        thickness_data['eficiencia_placas_min'] = thickness_data['total_placas'] / (thickness_data['tiempo_total_seg'] / 60)
        
        with col1:
            mejor_eficiencia_idx = thickness_data['eficiencia_placas_min'].idxmax()
            mejor_eficiencia_mm = thickness_data.loc[mejor_eficiencia_idx, 'espesor_mm']
            mejor_eficiencia_val = thickness_data.loc[mejor_eficiencia_idx, 'eficiencia_placas_min']
            st.markdown("""
            <div style="background: linear-gradient(90deg, #2C3E50 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🚀 Más Eficiente</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:.1f} placas/min</p>
            </div>
            """.format(int(mejor_eficiencia_mm), mejor_eficiencia_val), unsafe_allow_html=True)
        
        with col2:
            max_variabilidad_idx = thickness_data.apply(
                lambda row: (row['duracion_max_seg'] - row['duracion_min_seg']) / row['duracion_promedio_seg'] if row['duracion_promedio_seg'] > 0 else 0, 
                axis=1
            ).idxmax()
            max_variabilidad_mm = thickness_data.loc[max_variabilidad_idx, 'espesor_mm']
            variabilidad_val = ((thickness_data.loc[max_variabilidad_idx, 'duracion_max_seg'] - thickness_data.loc[max_variabilidad_idx, 'duracion_min_seg']) 
                               / thickness_data.loc[max_variabilidad_idx, 'duracion_promedio_seg']) * 100
            st.markdown("""
            <div style="background: linear-gradient(90deg, #A23B72 0%, #C73E1D 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">📊 Más Variable</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:.0f}% variación</p>
            </div>
            """.format(int(max_variabilidad_mm), variabilidad_val), unsafe_allow_html=True)
        
        with col3:
            mejor_aprovechamiento_idx = thickness_data['placas_por_corte'].idxmax()
            mejor_aprovechamiento_mm = thickness_data.loc[mejor_aprovechamiento_idx, 'espesor_mm']
            aprovechamiento_val = thickness_data.loc[mejor_aprovechamiento_idx, 'placas_por_corte']
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F18F01 0%, #F7B801 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">📈 Mejor Aprovechamiento</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{} mm</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">{:.1f} placas/corte</p>
            </div>
            """.format(int(mejor_aprovechamiento_mm), aprovechamiento_val), unsafe_allow_html=True)
        
        with col4:
            total_jobs_unicos = thickness_data['jobs_unicos'].sum()
            st.markdown("""
            <div style="background: linear-gradient(90deg, #85C1E9 0%, #A23B72 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🔧 Diversidad de Jobs</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Diseños únicos</p>
            </div>
            """.format(int(total_jobs_unicos)), unsafe_allow_html=True)
        
        # ==================== SECCIÓN 2: ANÁLISIS COMPARATIVO ====================
        st.markdown("---")
        st.subheader("📊 Análisis Comparativo por Material")
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig_volume = px.bar(thickness_data, x='espesor_mm', y='total_placas',
                               title='📊 Total de Placas por Espesor',
                               labels={'espesor_mm': 'Espesor (mm)', 'total_placas': 'Total Placas'},
                               color='total_placas',
                               color_continuous_scale=[[0, COLORS['info']], [1, COLORS['primary']]])
            fig_volume.update_layout(
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_volume, use_container_width=True)
        
        with col2:
            fig_efficiency = px.bar(thickness_data, x='espesor_mm', y='duracion_promedio_seg',
                                   title='⏱️ Duración Promedio por Espesor',
                                   labels={'espesor_mm': 'Espesor (mm)', 'duracion_promedio_seg': 'Segundos'},
                                   color='duracion_promedio_seg',
                                   color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_efficiency.update_layout(
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # ==================== SECCIÓN 3: ANÁLISIS AVANZADO ====================
        st.subheader("🔍 Métricas Avanzadas por Material")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de eficiencia (placas por minuto)
            fig_placas_min = px.bar(thickness_data, x='espesor_mm', y='eficiencia_placas_min',
                                   title='🚀 Eficiencia: Placas por Minuto',
                                   labels={'espesor_mm': 'Espesor (mm)', 'eficiencia_placas_min': 'Placas/min'},
                                   color='eficiencia_placas_min',
                                   color_continuous_scale=[[0, COLORS['warning']], [1, COLORS['success']]])
            fig_placas_min.update_layout(
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_placas_min, use_container_width=True)
        
        with col2:
            # Gráfico de aprovechamiento (placas por corte)
            fig_aprovechamiento = px.bar(thickness_data, x='espesor_mm', y='placas_por_corte',
                                        title='📈 Aprovechamiento: Placas por Corte',
                                        labels={'espesor_mm': 'Espesor (mm)', 'placas_por_corte': 'Placas/Corte'},
                                        color='placas_por_corte',
                                        color_continuous_scale=[[0, COLORS['info']], [1, COLORS['accent']]])
            fig_aprovechamiento.update_layout(
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_aprovechamiento, use_container_width=True)
        
        # ==================== SECCIÓN 4: TABLA DETALLADA ====================
        st.subheader("📋 Detalle Completo por Material")
        
        # Preparar datos para la tabla
        display_data = thickness_data.copy()
        display_data['Espesor (mm)'] = display_data['espesor_mm'].astype(int)
        display_data['Total Placas'] = display_data['total_placas'].astype(int)
        display_data['Total Cortes'] = display_data['total_cortes'].astype(int)
        display_data['Jobs Únicos'] = display_data['jobs_unicos'].astype(int)
        display_data['Tiempo Total (h)'] = (display_data['tiempo_total_seg'] / 3600).round(1)
        display_data['Duración Promedio (min)'] = (display_data['duracion_promedio_seg'] / 60).round(1)
        display_data['Placas/min'] = display_data['eficiencia_placas_min'].round(2)
        display_data['Placas/Corte'] = display_data['placas_por_corte'].round(1)
        
        # Mostrar tabla
        st.dataframe(
            display_data[['Espesor (mm)', 'Total Placas', 'Total Cortes', 'Jobs Únicos', 
                         'Tiempo Total (h)', 'Duración Promedio (min)', 'Placas/min', 'Placas/Corte']],
            use_container_width=True,
            hide_index=True
        )
        
    else:
        st.warning("No hay datos de espesores disponibles")

def show_jobs_analysis():
    st.header("🔧 Análisis por Jobs")
    create_kpi_explanation(
        "Análisis por Jobs",
        "Análisis detallado de cada tipo de trabajo procesado en la máquina. Cada 'job' representa un diseño o tipo de corte específico que puede repetirse en múltiples esquemas."
    )
    
    # ==================== SECCIÓN 1: KPIs GLOBALES DE JOBS ====================
    st.subheader("📊 KPIs Globales de Trabajos")
    
    # Consulta para métricas globales de jobs
    global_jobs_data = load_data("""
        WITH job_metrics AS (
            SELECT 
                job_key,
                COUNT(*) as total_cortes,
                SUM(cantidad_placas) as total_placas,
                AVG(duracion_segundos) as duracion_promedio_seg,
                SUM(duracion_segundos) as tiempo_total_seg,
                MIN(fecha_proceso) as primera_fecha,
                MAX(fecha_proceso) as ultima_fecha,
                AVG(largo_mm * ancho_mm) as area_promedio_mm2,
                AVG(espesor_mm) as espesor_promedio
            FROM cortes_seccionadora 
            GROUP BY job_key
        )
        SELECT 
            COUNT(*) as total_jobs_unicos,
            SUM(total_placas) as placas_totales,
            AVG(total_placas) as promedio_placas_por_job,
            SUM(tiempo_total_seg) as tiempo_total_segundos,
            AVG(duracion_promedio_seg) as duracion_global_promedio,
            MAX(total_placas) as max_placas_job,
            MIN(total_placas) as min_placas_job,
            COUNT(CASE WHEN total_cortes = 1 THEN 1 END) as jobs_ejecutados_una_vez,
            COUNT(CASE WHEN total_cortes > 10 THEN 1 END) as jobs_frecuentes
        FROM job_metrics
    """)
    
    if not global_jobs_data.empty:
        metrics = global_jobs_data.iloc[0]
        
        # Primera fila de KPIs globales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #2E86AB 0%, #A23B72 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🔧 Total Jobs Únicos</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Diseños diferentes</p>
            </div>
            """.format(int(metrics['total_jobs_unicos'])), unsafe_allow_html=True)
        
        with col2:
            tiempo_total_horas = metrics['tiempo_total_segundos'] / 3600
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F18F01 0%, #C73E1D 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">⏱️ Tiempo Total Jobs</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.0f}h</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Todos los trabajos</p>
            </div>
            """.format(tiempo_total_horas), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #85C1E9 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">📦 Promedio Placas/Job</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Placas por trabajo</p>
            </div>
            """.format(metrics['promedio_placas_por_job']), unsafe_allow_html=True)
        
        with col4:
            duracion_global_min = metrics['duracion_global_promedio'] / 60
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F7B801 0%, #F18F01 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">⚡ Duración Promedio</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">minutos/esquema</p>
            </div>
            """.format(duracion_global_min), unsafe_allow_html=True)
        
        # Segunda fila de KPIs de comportamiento
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #2C3E50 0%, #2E86AB 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🎯 Job Más Grande</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:,}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">placas máximo</p>
            </div>
            """.format(int(metrics['max_placas_job'])), unsafe_allow_html=True)
        
        with col2:
            porcentaje_unicos = (metrics['jobs_ejecutados_una_vez'] / metrics['total_jobs_unicos']) * 100
            st.markdown("""
            <div style="background: linear-gradient(90deg, #A23B72 0%, #C73E1D 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🔄 Jobs Únicos</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.0f}%</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Ejecutados 1 vez</p>
            </div>
            """.format(porcentaje_unicos), unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div style="background: linear-gradient(90deg, #F18F01 0%, #F7B801 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🔥 Jobs Frecuentes</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">Más de 10 ejecuciones</p>
            </div>
            """.format(int(metrics['jobs_frecuentes'])), unsafe_allow_html=True)
        
        with col4:
            eficiencia_global = metrics['placas_totales'] / (tiempo_total_horas * 60) if tiempo_total_horas > 0 else 0
            st.markdown("""
            <div style="background: linear-gradient(90deg, #85C1E9 0%, #A23B72 100%); 
                       padding: 1rem; border-radius: 10px; text-align: center; color: white; margin-bottom: 0.5rem;">
                <h3 style="margin: 0; font-size: 1.2rem;">🚀 Eficiencia Global</h3>
                <h2 style="margin: 0.2rem 0; font-size: 2rem; font-weight: bold;">{:.1f}</h2>
                <p style="margin: 0; font-size: 0.9rem; opacity: 0.9;">placas/min total</p>
            </div>
            """.format(eficiencia_global), unsafe_allow_html=True)
    
    # ==================== SECCIÓN 2: FILTROS Y CONFIGURACIÓN ====================
    st.markdown("---")
    st.subheader("🔍 Configuración de Análisis")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        top_n = st.selectbox("Mostrar top:", [10, 20, 50, 100], index=1, key="jobs_top_n")
    with col2:
        sort_by = st.selectbox("Ordenar por:", 
                              ["Total Placas", "Total Esquemas", "Tiempo Total", "Duración Promedio", "Eficiencia"],
                              index=0, key="jobs_sort")
    with col3:
        analisis_tipo = st.selectbox("Tipo de análisis:", 
                                   ["Todos los Jobs", "Jobs Frecuentes (>5 ejecuciones)", "Jobs Únicos (1 ejecución)"],
                                   index=0, key="jobs_filter")
    
    # Construir filtro adicional
    filtro_adicional = ""
    if analisis_tipo == "Jobs Frecuentes (>5 ejecuciones)":
        filtro_adicional = "HAVING COUNT(*) > 5"
    elif analisis_tipo == "Jobs Únicos (1 ejecución)":
        filtro_adicional = "HAVING COUNT(*) = 1"
    
    # Mapeo de opciones a columnas
    sort_mapping = {
        "Total Placas": "total_placas",
        "Total Esquemas": "total_cortes", 
        "Tiempo Total": "tiempo_total_seg",
        "Duración Promedio": "duracion_promedio_seg",
        "Eficiencia": "eficiencia_placas_min"
    }
    
    # ==================== SECCIÓN 3: DATOS DETALLADOS POR JOB ====================
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
            AVG(espesor_mm) as espesor_mm,
            MIN(duracion_segundos) as duracion_min_seg,
            MAX(duracion_segundos) as duracion_max_seg,
            SUM(cantidad_placas) / (SUM(duracion_segundos) / 60.0) as eficiencia_placas_min,
            AVG(largo_mm * ancho_mm * espesor_mm) as volumen_promedio_mm3
        FROM cortes_seccionadora 
        GROUP BY job_key 
        {filtro_adicional}
        ORDER BY {sort_mapping[sort_by]} DESC 
        LIMIT {top_n}
    """)
    
    if not jobs_data.empty:
        # ==================== SECCIÓN 4: ANÁLISIS VISUAL ====================
        st.subheader(f"📈 Top {min(15, len(jobs_data))} Jobs - Análisis Visual")
        
        # Truncar nombres largos para mejor visualización
        display_jobs = jobs_data.head(15).copy()
        display_jobs['job_key_short'] = display_jobs['job_key'].str[-30:]
        display_jobs['duracion_min'] = display_jobs['duracion_promedio_seg'] / 60
        display_jobs['tiempo_total_min'] = display_jobs['tiempo_total_seg'] / 60
        
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
            fig_top_jobs.update_layout(
                height=600, 
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_top_jobs, use_container_width=True)
        
        with col2:
            fig_duration = px.bar(display_jobs, 
                                 x='duracion_min', 
                                 y='job_key_short',
                                 orientation='h',
                                 title='⏱️ Duración Promedio por Corte (min)',
                                 labels={'duracion_min': 'Duración Promedio (min)', 'job_key_short': 'Job'},
                                 color='duracion_min',
                                 color_continuous_scale=[[0, COLORS['success']], [1, COLORS['warning']]])
            fig_duration.update_layout(
                height=600, 
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_duration, use_container_width=True)
        
        # ==================== SECCIÓN 5: ANÁLISIS DE EFICIENCIA Y PATRONES ====================
        st.subheader("🔍 Análisis de Eficiencia y Patrones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Gráfico de dispersión: total cortes vs eficiencia
            fig_scatter_efficiency = px.scatter(
                display_jobs,
                x='total_cortes',
                y='eficiencia_placas_min',
                size='total_placas',
                title='🔄 Repeticiones vs Eficiencia',
                labels={
                    'total_cortes': 'Total de Ejecuciones',
                    'eficiencia_placas_min': 'Eficiencia (placas/min)',
                    'total_placas': 'Total Placas'
                },
                color_discrete_sequence=[COLORS['secondary']],
                hover_data=['job_key_short', 'duracion_min']
            )
            fig_scatter_efficiency.update_layout(
                height=400,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_scatter_efficiency, use_container_width=True)
        
        with col2:
            # Gráfico de eficiencia pura
            top_efficiency_jobs = display_jobs.nlargest(15, 'eficiencia_placas_min')
            fig_efficiency = px.bar(
                top_efficiency_jobs,
                x='eficiencia_placas_min',
                y='job_key_short',
                orientation='h',
                title='🚀 Jobs Más Eficientes (placas/min)',
                labels={'eficiencia_placas_min': 'Placas por Minuto', 'job_key_short': 'Job'},
                color='eficiencia_placas_min',
                color_continuous_scale=[[0, COLORS['warning']], [1, COLORS['success']]]
            )
            fig_efficiency.update_layout(
                height=400,
                coloraxis_showscale=False,
                title_x=0.5,
                title_y=0.95,
                title_font_size=16,
                font=dict(family="Arial, sans-serif", size=12)
            )
            st.plotly_chart(fig_efficiency, use_container_width=True)
        
        # ==================== SECCIÓN 6: TABLA DETALLADA CON TODAS LAS MÉTRICAS ====================
        st.subheader("📋 Tabla Detallada de Jobs")
        
        # Preparar datos para la tabla
        table_data = jobs_data.copy()
        table_data['Job'] = table_data['job_key'].str[-40:]  # Mostrar últimos 40 caracteres
        table_data['Total Placas'] = table_data['total_placas'].astype(int)
        table_data['Ejecuciones'] = table_data['total_cortes'].astype(int)
        table_data['Tiempo Total (h)'] = (table_data['tiempo_total_seg'] / 3600).round(2)
        table_data['Duración Prom (min)'] = (table_data['duracion_promedio_seg'] / 60).round(1)
        table_data['Eficiencia (placas/min)'] = table_data['eficiencia_placas_min'].round(2)
        table_data['Material Prom (mm)'] = table_data['espesor_mm'].round(0).astype(int)
        table_data['Área Prom (cm²)'] = ((table_data['largo_mm'] * table_data['ancho_mm']) / 100).round(0).astype(int)
        table_data['Primera Ejecución'] = pd.to_datetime(table_data['primera_fecha']).dt.strftime('%d/%m/%Y')
        table_data['Última Ejecución'] = pd.to_datetime(table_data['ultima_fecha']).dt.strftime('%d/%m/%Y')
        
        # Mostrar tabla con paginación
        st.dataframe(
            table_data[['Job', 'Total Placas', 'Ejecuciones', 'Tiempo Total (h)', 
                       'Duración Prom (min)', 'Eficiencia (placas/min)', 'Material Prom (mm)', 
                       'Área Prom (cm²)', 'Primera Ejecución', 'Última Ejecución']],
            use_container_width=True,
            hide_index=True
        )
        
        # ==================== SECCIÓN 7: RESUMEN ESTADÍSTICO ====================
        st.subheader("📊 Resumen Estadístico de los Jobs Seleccionados")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Jobs Analizados", f"{len(jobs_data)}")
            st.metric("Placas Totales", f"{jobs_data['total_placas'].sum():,}")
        
        with col2:
            st.metric("Tiempo Total", f"{(jobs_data['tiempo_total_seg'].sum() / 3600):.1f}h")
            st.metric("Ejecuciones Totales", f"{jobs_data['total_cortes'].sum():,}")
        
        with col3:
            st.metric("Duración Prom.", f"{(jobs_data['duracion_promedio_seg'].mean() / 60):.1f} min")
            st.metric("Eficiencia Prom.", f"{jobs_data['eficiencia_placas_min'].mean():.2f} placas/min")
        
        with col4:
            st.metric("Job Más Repetido", f"{jobs_data['total_cortes'].max()} veces")
            st.metric("Rango de Materiales", f"{int(jobs_data['espesor_mm'].min())}-{int(jobs_data['espesor_mm'].max())} mm")
    
    else:
        st.warning(f"No hay datos de jobs disponibles para el filtro '{analisis_tipo}'")

# EJECUTAR EL DASHBOARD
main()
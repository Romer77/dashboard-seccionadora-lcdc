import streamlit as st

st.title("Dashboard Seccionadora - LCDC Mendoza")

# Import con manejo de error
try:
    from database import DATABASE_URL, ENGINE
    
    if ENGINE is None:
        st.error("No se pudo conectar a la base de datos")
        st.info("Verifica la configuración de secrets")
        st.stop()
    else:
        st.success("Base de datos conectada correctamente")
        
except ImportError as e:
    st.error(f"Error importando database module: {e}")
    st.stop()
except Exception as e:
    st.error(f"Error de configuración: {e}")
    st.stop()

# Resto de tu dashboard aquí...
st.write("Dashboard funcionando correctamente")

# Test básico de consulta
try:
    import pandas as pd
    from sqlalchemy import text
    
    with ENGINE.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
        table_count = result.fetchone()[0]
    
    st.info(f"Tablas disponibles en la base de datos: {table_count}")
    
except Exception as e:
    st.warning(f"No se pudieron consultar las tablas: {str(e)[:100]}...")
import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine

def get_database_connection():
    """Obtiene URL de pooler IPv4-compatible"""
    try:
        # Usar pooler en lugar de conexión directa
        base_url = st.secrets["PG_CONN"]
        
        # Asegurar SSL
        if "sslmode" not in base_url:
            return base_url + "?sslmode=require"
        return base_url
        
    except Exception as e:
        st.error(f"Error obteniendo PG_CONN: {e}")
        return None

def create_db_engine():
    """Crea engine con diagnóstico completo"""
    database_url = get_database_connection()
    
    if not database_url:
        return None
    
    # DEBUG: Mostrar que URL está usando (sin password)
    safe_url = database_url.replace(database_url.split('@')[0].split(':')[-1], "***")
    st.write(f"🔗 **URL de conexión:** {safe_url}")
    
    # Verificar si es pooler o direct connection
    if "pooler.supabase.com" in database_url:
        st.success("✅ Usando Transaction Pooler (IPv4)")
    elif "db.cyjracwepjzzeygfpbxr" in database_url:
        st.warning("⚠️ Usando Direct Connection (IPv6) - Cambiar a pooler")
    
    try:
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            connect_args={"sslmode": "require"}
        )
        
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT version()")).fetchone()
        
        st.success("✅ Conexión exitosa a PostgreSQL")
        return engine
        
    except Exception as e:
        st.error(f"❌ Error específico: {str(e)}")
        # Intentar sin SSL como fallback
        try:
            engine_no_ssl = create_engine(database_url.replace("?sslmode=require", ""))
            with engine_no_ssl.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            st.warning("⚠️ Conexión exitosa sin SSL")
            return engine_no_ssl
        except Exception as e2:
            st.error(f"❌ Error sin SSL: {str(e2)}")
        return None

DATABASE_URL = get_database_connection()
ENGINE = create_db_engine() if DATABASE_URL else None
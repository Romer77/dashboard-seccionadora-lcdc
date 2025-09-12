import streamlit as st
import sqlalchemy
from sqlalchemy import create_engine
import socket
from contextlib import contextmanager

def get_database_connection():
    """Obtiene URL con timeout"""
    try:
        return st.secrets["PG_CONN"]
    except Exception as e:
        st.error(f"Error obteniendo PG_CONN: {e}")
        return None

@contextmanager
def timeout_context(seconds=10):
    """Context manager para timeout"""
    import signal
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operación timeout después de {seconds} segundos")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)

def create_db_engine():
    """Crea engine con timeout estricto"""
    database_url = get_database_connection()
    
    if not database_url:
        return None
    
    try:
        # Timeout de 5 segundos máximo
        with timeout_context(5):
            engine = create_engine(
                database_url,
                connect_args={
                    "connect_timeout": 5,
                    "sslmode": "require"
                },
                pool_timeout=5,
                pool_pre_ping=False  # Evitar ping adicional
            )
            
            # Test rápido de conexión
            with engine.connect() as conn:
                conn.execute(sqlalchemy.text("SELECT 1"))
            
            st.success("✅ Conexión DB exitosa")
            return engine
            
    except TimeoutError:
        st.error("❌ Timeout conectando a base de datos")
        return None
    except Exception as e:
        st.error(f"❌ Error DB: {str(e)[:100]}...")
        return None

# Crear engine al inicio
DATABASE_URL = get_database_connection()
ENGINE = create_db_engine() if DATABASE_URL else None
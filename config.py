"""
Configuración centralizada para Dashboard Seccionadora LCDC
Maneja variables de entorno y configuración de producción
"""

import os
import streamlit as st
from typing import Optional
import logging


class Config:
    """Clase de configuración centralizada"""
    
    def __init__(self):
        self.environment = self._get_environment()
        self.database_url = self._get_database_url()
        self.app_title = "Dashboard Seccionadora - LCDC"
        self.cache_ttl = 300  # 5 minutos
        self.log_level = self._get_log_level()
        
    def _get_environment(self) -> str:
        """Detecta el entorno de ejecución"""
        # Primero revisar variable de entorno explícita
        if os.getenv("ENVIRONMENT"):
            return os.getenv("ENVIRONMENT")
        # Luego detectar Streamlit Cloud por variables del sistema
        elif self._is_streamlit_cloud():
            return "streamlit_cloud"
        else:
            return "local"
    
    def _is_streamlit_cloud(self) -> bool:
        """Detecta si está ejecutándose en Streamlit Cloud"""
        # Verificar variables de entorno específicas de Streamlit Cloud
        streamlit_cloud_indicators = [
            "STREAMLIT_SERVER_PORT",
            "STREAMLIT_SERVER_ADDRESS", 
            "_STREAMLIT_INTERNAL_"
        ]
        
        # Si alguna variable específica de Streamlit Cloud existe
        for indicator in streamlit_cloud_indicators:
            if os.getenv(indicator):
                return True
                
        # Método secundario: verificar si secrets está disponible
        try:
            if hasattr(st, 'secrets'):
                # Intentar acceder a secrets sin usar atributos privados
                st.secrets.get("_test", None)
                return True
        except Exception:
            pass
            
        return False
    
    def _get_database_url(self) -> Optional[str]:
        """Obtiene la URL de base de datos según el entorno"""
        if self._is_streamlit_cloud():
            # En Streamlit Cloud usar secrets
            try:
                return st.secrets["database"]["PG_CONN"]
            except KeyError:
                st.error("❌ Error: Variable PG_CONN no encontrada en Streamlit secrets")
                st.info("💡 Configura PG_CONN en los secrets de tu app en Streamlit Cloud")
                return None
            except Exception:
                st.error("❌ Error: No se pueden leer los secrets de Streamlit")
                return None
        else:
            # En desarrollo local usar .env
            try:
                from dotenv import load_dotenv
                load_dotenv()
            except ImportError:
                # Si no está python-dotenv, continuar sin .env
                pass
            
            db_url = os.getenv("PG_CONN")
            # Solo mostrar error si realmente no existe la variable
            # El método validate_config se encargará de la validación completa
            return db_url
    
    def _get_log_level(self) -> str:
        """Obtiene el nivel de logging"""
        if self._is_streamlit_cloud():
            try:
                return st.secrets.get("LOG_LEVEL", "INFO")
            except Exception:
                return "INFO"
        else:
            return os.getenv("LOG_LEVEL", "INFO")
    
    def validate_config(self) -> bool:
        """Valida que la configuración sea correcta"""
        if not self.database_url:
            st.warning("⚠️ Variable PG_CONN no configurada")
            return False
        
        # Validar formato básico de URL de PostgreSQL
        if not self.database_url.startswith(("postgresql://", "postgres://")):
            st.error("❌ Error: PG_CONN debe ser una URL de PostgreSQL válida")
            st.info("💡 Formato: postgresql://usuario:contraseña@host:puerto/database")
            return False
            
        return True
    
    def get_database_config(self) -> dict:
        """Retorna configuración específica de base de datos"""
        return {
            "url": self.database_url,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600  # 1 hora
        }
    
    def get_streamlit_config(self) -> dict:
        """Retorna configuración específica de Streamlit"""
        return {
            "page_title": self.app_title,
            "page_icon": "🏭",
            "layout": "wide",
            "initial_sidebar_state": "expanded"
        }


# Instancia global de configuración
config = Config()


def setup_logging():
    """Configura el sistema de logging"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurar logger principal
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format=log_format
    )
    
    # Logger específico para la aplicación
    logger = logging.getLogger("seccionadora_dashboard")
    logger.setLevel(getattr(logging, config.log_level.upper()))
    
    return logger


def get_logger(name: str = "seccionadora_dashboard") -> logging.Logger:
    """Obtiene un logger configurado"""
    return logging.getLogger(name)
# Dashboard Seccionadora - Deployment Guide

## 🚀 Deploy en Streamlit Community Cloud

### Preparación del Proyecto

1. **Subir código a GitHub**
   ```bash
   git init
   git add .
   git commit -m "Dashboard seccionadora inicial"
   git branch -M main
   git remote add origin https://github.com/tu-usuario/seccionadora-dashboard.git
   git push -u origin main
   ```

2. **Configurar variables de entorno en Streamlit Cloud**
   - Ve a [share.streamlit.io](https://share.streamlit.io)
   - Conecta tu repositorio de GitHub
   - En "Advanced settings", agrega:
     ```
     PG_CONN = postgresql://usuario:contraseña@hostname:port/seccionadora_logs
     ```

### Estructura de Archivos

```
Seccionadora/
├── dashboard_streamlit.py          # Dashboard principal
├── requirements.txt                # Dependencias Python
├── .streamlit/config.toml         # Configuración Streamlit
├── .env.example                   # Ejemplo de variables de entorno
├── README_DEPLOYMENT.md           # Esta guía
├── etl_secc.py                   # ETL existente
└── init_database.sql             # Schema de DB
```

### Configuración de Base de Datos

#### Opción 1: PostgreSQL Existente
- Usar tu servidor PostgreSQL actual
- Configurar `PG_CONN` con tu string de conexión

#### Opción 2: Base de Datos en la Nube (Recomendado para producción)
- **Supabase** (gratuito): https://supabase.com
- **Railway** ($5/mes): https://railway.app
- **Render** ($7/mes): https://render.com

### Pasos de Deployment

1. **Subir a GitHub** (repositorio público para versión gratuita)

2. **Conectar con Streamlit Cloud**
   - Ir a https://share.streamlit.io
   - "New app" → Conectar repositorio
   - Main file: `dashboard_streamlit.py`

3. **Configurar Variables de Entorno**
   ```
   PG_CONN = postgresql://usuario:contraseña@host:puerto/seccionadora_logs
   ```

4. **Deploy Automático** 
   - Streamlit Cloud hace deploy automáticamente
   - Cada push a main actualiza la app

### URLs de Ejemplo

- **Tu app**: `https://tu-usuario-seccionadora-dashboard-main-dashboard-streamlit-xxxx.streamlit.app`
- **Dominio personalizado**: Configurar CNAME en tu dominio

### Seguridad

- ✅ Variables de entorno protegidas
- ✅ Conexión SSL automática  
- ✅ No exposición de credenciales en código
- ⚠️  Repositorio público (limitación versión gratuita)

### Mantenimiento

- **Actualizaciones**: Push a main actualiza automáticamente
- **Monitoreo**: Logs disponibles en Streamlit Cloud dashboard
- **Secrets**: Cambiar en settings de la app

### Troubleshooting

**Error de conexión a DB:**
```
PG_CONN mal configurado → Verificar string de conexión
```

**Dependencias faltantes:**
```
Agregar a requirements.txt y hacer push
```

**App no carga:**
```
Verificar logs en Streamlit Cloud dashboard
```

### Contacto
Para problemas técnicos, revisar logs en Streamlit Cloud o contactar soporte.
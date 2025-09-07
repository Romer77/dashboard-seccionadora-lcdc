# Guía de Deployment - Dashboard Seccionadora LCDC

## 🎯 Objetivo
Esta guía permite deployar el Dashboard de Seccionadora en **Streamlit Community Cloud** de forma confiable y escalable para cualquier sucursal de LCDC.

## 📋 Prerrequisitos

### Accesos Necesarios
- [ ] Cuenta GitHub (crear en github.com si no existe)
- [ ] Acceso a Streamlit Cloud (share.streamlit.io)  
- [ ] Credenciales de base de datos PostgreSQL
- [ ] Persona técnica designada para deployment

### Datos Requeridos
```bash
# Información de base de datos
Host: [IP o dominio del servidor PostgreSQL]
Puerto: [generalmente 5432]
Base de datos: seccionadora_logs
Usuario: [usuario con permisos de lectura]
Contraseña: [contraseña del usuario]
```

## 🚀 Proceso de Deployment

### Paso 1: Preparar el Código en GitHub

1. **Crear repositorio en GitHub**
   ```bash
   # En github.com crear nuevo repositorio:
   # Nombre: dashboard-seccionadora-[SUCURSAL]
   # Tipo: Public (requerido para Streamlit Cloud gratuito)
   ```

2. **Subir código al repositorio**
   ```bash
   # Clonar este proyecto
   git clone [URL_ESTE_REPOSITORIO]
   cd dashboard-seccionadora
   
   # Cambiar origin al nuevo repositorio
   git remote set-url origin https://github.com/[TU_USUARIO]/dashboard-seccionadora-[SUCURSAL].git
   
   # Subir código
   git push -u origin main
   ```

### Paso 2: Configurar Streamlit Cloud

1. **Conectar repositorio**
   - Ir a https://share.streamlit.io
   - Hacer clic en "New app"
   - Conectar con GitHub
   - Seleccionar el repositorio creado
   - Main file path: `dashboard_streamlit.py`

2. **Configurar Secrets** (⚠️ CRÍTICO)
   - En la configuración de la app, ir a "Secrets"
   - Agregar la siguiente configuración:
   ```toml
   [database]
   PG_CONN = "postgresql://usuario:contraseña@host:puerto/seccionadora_logs"
   
   LOG_LEVEL = "INFO"
   ```

### Paso 3: Validar Deployment

1. **Verificar conexión**
   - La app debe cargar sin errores
   - Verificar que aparezca "STREAMLIT_CLOUD" en el header
   - Confirmar que los datos se cargan correctamente

2. **Testear funcionalidades**
   - [ ] Overview General: KPIs principales
   - [ ] Análisis Diario: filtros de fecha
   - [ ] Análisis por Espesores: gráficos
   - [ ] Análisis por Jobs: tablas y visualizaciones

## 🔧 Configuración de Base de Datos

### Opción A: PostgreSQL Local/Red Interna
```sql
-- Crear usuario específico para dashboard (recomendado)
CREATE USER dashboard_user WITH PASSWORD 'contraseña_segura';
GRANT CONNECT ON DATABASE seccionadora_logs TO dashboard_user;
GRANT USAGE ON SCHEMA public TO dashboard_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO dashboard_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO dashboard_user;
```

### Opción B: Base de Datos en la Nube
- **Supabase** (recomendado - gratis hasta 2GB)
- **Railway** ($5/mes - más confiable)
- **Render** ($7/mes - PostgreSQL managed)

## 📊 Monitoreo y Mantenimiento

### Logs de Aplicación
- **Streamlit Cloud**: Ver logs en el dashboard de la app
- **Errores comunes**: Documentados en la sección troubleshooting

### Actualizaciones
```bash
# Para actualizar la aplicación:
git add .
git commit -m "Actualización: [descripción]"
git push origin main

# Streamlit Cloud redeploya automáticamente
```

### Backup de Datos
```sql
-- Backup diario recomendado
pg_dump -h host -U usuario -d seccionadora_logs > backup_$(date +%Y%m%d).sql
```

## 🔒 Seguridad y Buenas Prácticas

### Configuración de Secrets
- ✅ **NUNCA** commitear contraseñas al repositorio
- ✅ Usar secrets de Streamlit Cloud para credenciales
- ✅ Usar usuarios de base de datos con permisos mínimos (solo SELECT)
- ✅ Cambiar contraseñas periódicamente

### Acceso y Permisos
- **URL de la app**: Compartir solo con personal autorizado
- **Repositorio GitHub**: Mantener como público (limitación gratuita)
- **Secrets**: Solo administradores pueden modificar

## 🚨 Troubleshooting

### Error: "No se pudo conectar a la base de datos"
```bash
Verificar:
1. ✅ PG_CONN está configurado correctamente en secrets
2. ✅ Host y puerto son accesibles desde internet
3. ✅ Usuario y contraseña son correctos
4. ✅ Base de datos "seccionadora_logs" existe
```

### Error: "Tabla no encontrada"
```bash
Solución:
1. Ejecutar init_database.sql en la base de datos
2. Verificar que las tablas y vistas existen
3. Confirmar permisos del usuario dashboard_user
```

### App muy lenta
```bash
Optimizaciones:
1. Verificar que los índices existen (ver init_database.sql)
2. Considerar migrar a base de datos en la nube
3. Reducir rango de fechas en consultas
```

### Límites de Streamlit Cloud
```bash
Límites conocidos:
- CPU: 1 core compartido
- RAM: 1GB máximo
- Ancho de banda: Limitado
- Uptime: 99% (servicio gratuito)
```

## 📈 Escalabilidad y Mejoras

### Para Más de 1 Sucursal
1. **Un repositorio por sucursal** (recomendado)
2. **Configuración por entorno** usando variables
3. **Base de datos centralizada** con filtros por sucursal

### Migraciones Futuras
```bash
# Si se requiere mayor control, migrar a:
- VPS con Docker + Nginx
- Azure App Service
- AWS ECS
- Railway/Render con Docker
```

## 📞 Soporte Técnico

### Contactos LCDC
- **Administrador Sistema**: [nombre@lcdc.com]
- **Responsable IT**: [it@lcdc.com]
- **Desarrollador**: [dev@lcdc.com]

### Recursos Adicionales
- 📖 [Documentación Streamlit Cloud](https://docs.streamlit.io/streamlit-community-cloud)
- 🔧 [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- 🎯 [Troubleshooting GitHub Actions](https://docs.github.com/en/actions)

---

## ✅ Checklist de Deployment Exitoso

- [ ] Repositorio GitHub creado y código subido
- [ ] App desplegada en Streamlit Cloud
- [ ] Secrets configurados correctamente
- [ ] Base de datos accesible desde internet
- [ ] Todos los KPIs cargan datos reales
- [ ] Usuario técnico capacitado en mantenimiento
- [ ] Documentación entregada al equipo
- [ ] Plan de backup implementado

**🎉 ¡Deployment completado exitosamente!**

---

*Guía creada para LCDC - Dashboard Seccionadora MDF*
*Versión: 1.0 - Fecha: 2025*
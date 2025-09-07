@echo off
echo Exportando datos de PostgreSQL local...

rem Verificar si pg_dump está disponible
where pg_dump >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: pg_dump no encontrado. 
    echo Instala PostgreSQL tools o usa la opción manual.
    pause
    exit /b 1
)

rem Exportar solo los datos de la tabla
pg_dump -h localhost -U postgres -d seccionadora_logs -t cortes_seccionadora --data-only --inserts -f supabase_data_insert.sql

if %errorlevel% equ 0 (
    echo ✅ Datos exportados exitosamente en: supabase_data_insert.sql
    echo 📝 Próximo paso: Ejecutar este archivo en Supabase SQL Editor
) else (
    echo ❌ Error exportando datos
)

pause
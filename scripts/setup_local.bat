@echo off
setlocal enabledelayedexpansion

echo ==========================================================
echo 🏔️  CryptoLake - Instalador Personalizado (Windows)
echo ==========================================================
echo.

set "DEFAULT_PATH=%CD%"
echo Directorio actual: %DEFAULT_PATH%
set /p "INSTALL_DIR=¿Donde quieres instalar el proyecto? (Enter para usar actual): "

if "%INSTALL_DIR%"=="" set "INSTALL_DIR=%DEFAULT_PATH%"

if not exist "%INSTALL_DIR%" (
    echo Creando directorio: %INSTALL_DIR%
    mkdir "%INSTALL_DIR%"
)

cd /d "%INSTALL_DIR%"
echo.
echo [1/4] Verificando Docker...
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker no esta instalado o no esta funcionando.
    pause
    exit /b
)

echo [2/4] Preparando entorno en: %INSTALL_DIR%
# Si el usuario eligio una carpeta nueva, podriamos clonar/mover aqui, 
# pero asumimos que el .bat se mueve con el repo.
echo.

echo [3/4] Levantando infraestructura base...
# Crear .env si no existe
if not exist ".env" (
    echo Creando archivo .env por defecto...
    echo PROJECT_PATH=%INSTALL_DIR% > .env
    echo LAKE_STORAGE=%INSTALL_DIR%/data >> .env
)

docker-compose up -d minio kafka redis iceberg-rest prometheus grafana

echo Esperando validacion de servicios...
timeout /t 10 /nobreak >nul

echo [4/4] Levantando aplicaciones y procesamiento...
docker-compose up -d

echo.
echo [EXTRA] ¿Deseas ejecutar un entrenamiento inicial (ML)?
echo (Solo recomendado si ya hay datos en el Spark streaming)
set /p "TRAIN_NOW=Presiona 'S' para entrenar ahora o Enter para saltar: "

if /i "%TRAIN_NOW%"=="S" (
    echo Entrenando memoria HISTORICA...
    docker exec cryptolake-ml python src/ml/train.py historical
    echo Entrenando memoria RECIENTE...
    docker exec cryptolake-ml python src/ml/train.py recent
)

echo.
echo ==========================================================
echo ✅ Instalacion y despliegue completado en:
echo %INSTALL_DIR%
echo.
echo Dashboard:  http://localhost:8501
echo API REST:   http://localhost:8000/docs
echo Airflow:    http://localhost:8080 (Admin:admin)
echo ==========================================================
pause

echo ==========================================================
pause

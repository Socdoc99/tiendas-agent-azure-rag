@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul

for %%I in ("%~dp0..") do set "PROJECT_ROOT=%%~fI"
pushd "%PROJECT_ROOT%" || (
  echo ERROR: No se pudo abrir la carpeta del proyecto.
  exit /b 1
)

set "EXPECTED_SUBSCRIPTION=6be99cce-254f-4377-9907-416ffe20833c"
set "EXPECTED_ACCOUNT=santiago9902@hotmail.com"
set "RESOURCE_GROUP=rg-tiendas-agent-sbx"
set "FOUNDRY_ACCOUNT=ai-tiendas-agent-sbx-k7m4p2"
set "FOUNDRY_PROJECT=tiendason-agent-sbx"
set "ENVIRONMENT=cae-tiendas-agent-sbx"
set "DEPLOYMENT=tiendas-agent-env-retry"

:menu
cls
echo ============================================================
echo Tiendas Agent Azure RAG - flujo local y preflight
echo ============================================================
echo 1. Preparar entorno local
echo 2. Verificar sesion, repo y herramientas
echo 3. Ejecutar pruebas y lint
echo 4. Ejecutar API local
echo 5. Construir imagen Docker local
echo 6. Consultar estado Azure (solo lectura)
echo 7. Verificar Bicep y revisar What-If (sin aplicar)
echo 8. Ver fases y gate actual
echo 0. Salir
echo.
choice /c 123456780 /n /m "Selecciona una opcion: "
if errorlevel 9 goto :done
if errorlevel 8 goto :roadmap
if errorlevel 7 goto :azure_whatif
if errorlevel 6 goto :azure_status
if errorlevel 5 goto :docker_build
if errorlevel 4 goto :run_api
if errorlevel 3 goto :local_checks
if errorlevel 2 goto :preflight
if errorlevel 1 goto :setup
goto :menu

:setup
echo.
echo [Setup] Python 3.11 y dependencias locales
where py >nul 2>nul || (echo ERROR: No se encontro el launcher py.& goto :pause_menu)
py -3.11 --version || goto :pause_menu
if not exist ".venv\Scripts\python.exe" (
  py -3.11 -m venv .venv || goto :pause_menu
)
".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt || goto :pause_menu
if not exist ".env" (
  copy /Y ".env.example" ".env" >nul || goto :pause_menu
  echo Se creo .env desde .env.example. Completa la configuracion local sin guardar secretos en Git.
) else (
  echo .env ya existe; no se sobrescribio.
)
echo Setup local completado.
goto :pause_menu

:preflight
echo.
echo [Preflight] Rama y cambios locales
git branch --show-current
git status --short --branch
echo.
echo [Preflight] Azure CLI
set "AZ_SUBSCRIPTION="
for /f "usebackq delims=" %%S in (`az account show --query id -o tsv 2^>nul`) do set "AZ_SUBSCRIPTION=%%S"
if not defined AZ_SUBSCRIPTION (
  echo No hay sesion Azure CLI valida. Inicia sesion manualmente con:
  echo   az login --tenant 8d436e95-814f-4786-bc1b-9f0d627ca3bd
) else (
  echo Suscripcion activa: %AZ_SUBSCRIPTION%
  if /I not "%AZ_SUBSCRIPTION%"=="%EXPECTED_SUBSCRIPTION%" echo AVISO: No coincide con la suscripcion objetivo.
  set "AZ_LOGIN="
  for /f "usebackq delims=" %%U in (`az account show --query user.name -o tsv 2^>nul`) do set "AZ_LOGIN=%%U"
  echo Cuenta Azure CLI: !AZ_LOGIN!
  if /I not "!AZ_LOGIN!"=="%EXPECTED_ACCOUNT%" echo AVISO: No coincide con la cuenta objetivo.
)
echo.
echo [Preflight] Azure Developer CLI
azd auth login --check-status
if errorlevel 1 echo No hay sesion azd valida. Inicia sesion manualmente con: azd auth login --tenant-id 8d436e95-814f-4786-bc1b-9f0d627ca3bd
set "AZD_SUBSCRIPTION="
for /f "usebackq delims=" %%S in (`azd config get defaults.subscription 2^>nul`) do set "AZD_SUBSCRIPTION=%%S"
if defined AZD_SUBSCRIPTION (
  echo Suscripcion configurada en azd: %AZD_SUBSCRIPTION%
  if /I not "%AZD_SUBSCRIPTION%"=="%EXPECTED_SUBSCRIPTION%" echo AVISO: No coincide con la suscripcion objetivo.
) else (
  echo No se pudo leer defaults.subscription de azd.
)
echo.
echo [Preflight] Resource providers requeridos (solo consulta)
for %%P in (Microsoft.CognitiveServices Microsoft.ContainerRegistry Microsoft.Compute Microsoft.ManagedIdentity Microsoft.Network Microsoft.Search Microsoft.Storage Microsoft.KeyVault Microsoft.App Microsoft.OperationalInsights Microsoft.Insights) do (
  for /f "usebackq delims=" %%R in (`az provider show --namespace %%P --query registrationState -o tsv 2^>nul`) do echo %%P: %%R
)
echo.
echo [Preflight] Python y Docker
py -3.11 --version
docker version
echo.
echo [Preflight] Extensiones Foundry de azd
azd ai agent version
azd ai project version
azd ai connection version
echo.
echo [Preflight] Roles en la suscripcion objetivo
az role assignment list --assignee "%EXPECTED_ACCOUNT%" --scope "/subscriptions/%EXPECTED_SUBSCRIPTION%" --query "[].roleDefinitionName" -o tsv
goto :pause_menu

:local_checks
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta primero la opcion 1 para preparar .venv.
  goto :pause_menu
)
echo [Checks] pytest
".venv\Scripts\python.exe" -m pytest
if errorlevel 1 goto :check_failed
echo.
echo [Checks] Ruff
".venv\Scripts\ruff.exe" check .
if errorlevel 1 goto :check_failed
echo.
echo Checks locales completados correctamente.
goto :pause_menu

:check_failed
echo ERROR: Una comprobacion fallo. Revisa la salida antes de continuar.
goto :pause_menu

:run_api
echo.
if not exist ".venv\Scripts\python.exe" (
  echo Ejecuta primero la opcion 1 para preparar .venv.
  goto :pause_menu
)
echo La API se ejecutara localmente. Usa Ctrl+C para detenerla.
".venv\Scripts\python.exe" -m uvicorn app.main:app --reload
goto :pause_menu

:docker_build
echo.
docker version >nul 2>nul || (echo ERROR: Docker no esta disponible.& goto :pause_menu)
docker build -t tiendas-agent-azure-rag:local .
if errorlevel 1 echo ERROR: Fallo el build de Docker.
goto :pause_menu

:azure_status
echo.
echo [Solo lectura] Resource Group
az group show --name "%RESOURCE_GROUP%" --query "{name:name,location:location,state:properties.provisioningState}" -o table
echo.
echo [Solo lectura] Foundry account existente
az cognitiveservices account show --resource-group "%RESOURCE_GROUP%" --name "%FOUNDRY_ACCOUNT%" --query "{name:name,kind:kind,state:properties.provisioningState}" -o table
echo.
echo [Solo lectura] Foundry project existente
az cognitiveservices account project show --resource-group "%RESOURCE_GROUP%" --name "%FOUNDRY_ACCOUNT%" --project-name "%FOUNDRY_PROJECT%" --query "{name:name,state:properties.provisioningState}" -o table
echo.
echo [Solo lectura] Container Apps Environment
az containerapp env show --resource-group "%RESOURCE_GROUP%" --name "%ENVIRONMENT%" --query "{name:name,state:properties.provisioningState,error:properties.deploymentErrors}" -o json
echo.
echo [Solo lectura] Reintento ARM
az deployment group show --resource-group "%RESOURCE_GROUP%" --name "%DEPLOYMENT%" --query "{state:properties.provisioningState,error:properties.error}" -o json
echo.
echo Esta opcion no crea ni modifica recursos.
goto :pause_menu

:azure_whatif
echo.
set "RETRY_STATE="
for /f "usebackq delims=" %%S in (`az deployment group show --resource-group "%RESOURCE_GROUP%" --name "%DEPLOYMENT%" --query properties.provisioningState -o tsv 2^>nul`) do set "RETRY_STATE=%%S"
set "ENV_STATE="
for /f "usebackq delims=" %%S in (`az containerapp env show --resource-group "%RESOURCE_GROUP%" --name "%ENVIRONMENT%" --query properties.provisioningState -o tsv 2^>nul`) do set "ENV_STATE=%%S"
if /I "!RETRY_STATE!"=="Running" (
  echo BLOQUEADO: deployment ARM sigue Running. No se iniciara ninguna operacion Bicep.
  goto :pause_menu
)
if /I "!ENV_STATE!"=="Updating" (
  echo BLOQUEADO: Container Apps Environment sigue Updating. No se iniciara ninguna operacion Bicep.
  goto :pause_menu
)
echo [Bicep] Compilacion local
az bicep build --file infra\core.bicep --stdout >nul
if errorlevel 1 (echo ERROR: Bicep no compilo.& goto :pause_menu)
echo [Bicep] Validacion ARM (no aplica recursos)
az deployment group validate --resource-group "%RESOURCE_GROUP%" --name tiendas-agent-core-review --template-file infra\core.bicep --parameters searchSku=free dataLocation=eastus appLocation=eastus
if errorlevel 1 (echo ERROR: La validacion ARM fallo.& goto :pause_menu)
echo.
echo [Bicep] What-If (no aplica recursos). Revisa cada cambio antes de autorizar un despliegue.
az deployment group what-if --resource-group "%RESOURCE_GROUP%" --name tiendas-agent-core-review --template-file infra\core.bicep --parameters searchSku=free dataLocation=eastus appLocation=eastus
goto :pause_menu

:roadmap
echo.
echo Fase 0 - PASS: preflight registrado en IMPLEMENTATION_LOG.md
echo Fase 1 - PASS: FastAPI base y verificaciones locales
echo Fase 2A - PASS: Core Infrastructure en el RG existente
echo Fase 2B - PENDIENTE: ACA en eastus sigue en deployment Running / Environment Updating
echo Fases 3 a 8 - ABIERTAS: ejecutar localmente contra los servicios Azure existentes
echo Fase 9 - BLOQUEADA: requiere Container Apps Environment operativo
echo Fases 10 y 11 - PENDIENTES segun los gates de despliegue y validacion
echo.
echo Detalle y fuente de verdad: IMPLEMENTATION_LOG.md y documentos del plan maestro.
echo Consulta opcion 6 antes de cualquier operacion Azure para refrescar el estado remoto.
goto :pause_menu

:pause_menu
echo.
pause
goto :menu

:done
popd
endlocal
exit /b 0

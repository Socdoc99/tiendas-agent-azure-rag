# Tiendas Agent Azure RAG

MVP para responder preguntas empresariales a partir de documentos, con retrieval-augmented generation sobre Azure AI Search.

El desarrollo ocurre en `develop`; `main` es la rama estable.

## Desarrollo local

Requiere Python 3.11 o superior. La imagen de producción usa Python 3.12.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

La aplicación permite consultar `/health` sin servicios externos. Para habilitar `/ready` y las funciones RAG, completa las variables de Azure y los nombres de modelos en `.env`. No guardes claves reales en Git.

## Comprobaciones

```powershell
python -m pytest
ruff check .
docker build -t tiendas-agent-azure-rag .
```

En Windows tambien puedes abrir el menu local y de preflight con [`scripts/workflow.bat`](scripts/workflow.bat). El menu no aplica despliegues Azure; revisa primero el estado remoto y exige `what-if` antes de cualquier futura operacion Bicep.

Flujo local: opción `1` prepara el entorno y crea `.env` sin sobrescribirlo; opción `2` consulta suscripción, recursos, providers, roles y herramientas; opción `3` ejecuta pytest y Ruff; opción `9` crea/actualiza el índice Search; opción `4` inicia la API. Con la API activa en una terminal, usa la opción `A` en otra ventana para subir e indexar un PDF, DOCX, TXT o MD. El índice está creado en el sandbox. La identidad actual todavía recibe 403 al consultar/escribir documentos Search y no puede leer el secreto de Key Vault, así que la ingesta real y el chat quedan pendientes de corregir el acceso de datos.

La Fase 2B de Container Apps sigue en curso remoto. No ejecutes Fase 9 hasta que `cae-tiendas-agent-sbx` esté operativo. Las Fases 3–8 se trabajan localmente; el detalle verificado está en [`IMPLEMENTATION_LOG.md`](IMPLEMENTATION_LOG.md).

Consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md) y [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) para la arquitectura y operación.

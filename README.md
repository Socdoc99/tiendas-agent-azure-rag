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

Consulta [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), [docs/SECURITY.md](docs/SECURITY.md) y [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) para la arquitectura y operación.

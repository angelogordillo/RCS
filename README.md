# Red de Cadena de Suministro México (RCS)

Proyecto inicial para visualizar, analizar y coordinar nodos logísticos en México (proveedores, plantas, centros de distribución, puertos, rutas y riesgo operativo).

## Objetivo
Construir una plataforma ligera para:
- mapear nodos de la cadena de suministro en México,
- monitorear indicadores clave (tiempo, costo, riesgo, capacidad),
- priorizar rutas y contingencias ante disrupciones.

## Alcance inicial (MVP)
- Catálogo de nodos y rutas.
- Dashboard con KPIs de red.
- API para consultar y registrar eventos de riesgo.
- Frontend web básico para visualización y operación.

## Estructura del proyecto
- `backend/`: API en FastAPI.
- `frontend/`: interfaz web estática inicial.
- `docs/`: arquitectura y lineamientos.
- `data/`: datasets de ejemplo.

## Requisitos
- Python 3.11+

## Ejecución local
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

Abrir `frontend/index.html` en el navegador o servirlo con cualquier servidor estático.

## Próximos pasos
1. Integrar base de datos (PostgreSQL + PostGIS opcional).
2. Agregar autenticación por roles (planeación, operaciones, compras).
3. Conectar fuentes externas (costos, clima, puertos, aduanas).

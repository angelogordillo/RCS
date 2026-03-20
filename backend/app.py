from pathlib import Path
from datetime import date
import base64
import hmac
import json
import os
import secrets

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="RCS API", version="0.1.0")
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_INDEX = BASE_DIR / "frontend" / "index.html"
FRONTEND_EVENTOS = BASE_DIR / "frontend" / "eventos.html"
FRONTEND_BOLSA = BASE_DIR / "frontend" / "bolsa.html"
FRONTEND_PUBLICACIONES = BASE_DIR / "frontend" / "publicaciones.html"
FRONTEND_PROYECCION = BASE_DIR / "frontend" / "proyeccion.html"
LOGOS_DIR = BASE_DIR / "logos"
COMPANY_USER = os.getenv("RCS_COMPANY_USER", "wildfoods")
COMPANY_PASSWORD = os.getenv("RCS_COMPANY_PASSWORD", "wildfoods2026")
COMPANY_NAME = os.getenv("RCS_COMPANY_NAME", "Wild Foods Mexico")
APP_SECRET = os.getenv("RCS_APP_SECRET", "rcs-company-secret")

if LOGOS_DIR.exists():
    app.mount("/logos", StaticFiles(directory=LOGOS_DIR), name="logos")


class Node(BaseModel):
    id: str
    nombre: str
    tipo: str
    estado: str
    capacidad: float


class CompanyLogin(BaseModel):
    company: str
    username: str
    password: str


NODES = [
    {
        "id": "mx-cdmx-cd-001",
        "nombre": "Centro de Distribución CDMX",
        "tipo": "centro_distribucion",
        "estado": "CDMX",
        "capacidad": 1500.0,
    },
    {
        "id": "mx-nl-planta-001",
        "nombre": "Planta Monterrey",
        "tipo": "planta",
        "estado": "Nuevo León",
        "capacidad": 3200.0,
    },
]

MONTHLY_FORECAST_DATA = [
    {"month": "Mar 2026", "final_fcst": 136772, "ma_fcst": 129374, "sales_order": 0, "py": 61365, "sku_count": 58, "flag": "YTG"},
    {"month": "Abr 2026", "final_fcst": 154481, "ma_fcst": 129374, "sales_order": 0, "py": 58565, "sku_count": 58, "flag": "YTG"},
    {"month": "May 2026", "final_fcst": 197476, "ma_fcst": 129374, "sales_order": 0, "py": 106858, "sku_count": 58, "flag": "YTG"},
    {"month": "Jun 2026", "final_fcst": 168873, "ma_fcst": 129374, "sales_order": 0, "py": 78543, "sku_count": 58, "flag": "YTG"},
]

SEGMENTATION_DATA = [
    {"region": "Market Intelligence", "share_pct": 42.3, "units_6m": 277985},
    {"region": "Pure Stat. Fcst", "share_pct": 28.4, "units_6m": 186960},
    {"region": "Alternative Strategies", "share_pct": 17.0, "units_6m": 111662},
    {"region": "Stat. Fcst", "share_pct": 12.3, "units_6m": 80995},
]

GROUP_FORECAST_DATA = [
    {"sku": "Barras", "canal": "LineName", "avg_monthly_units": 18, "peak_month": "Forecast", "peak_units": 466759, "revenue_mxn": 445648, "margin_pct": 203790, "py_units": 370295},
    {"sku": "Granola", "canal": "LineName", "avg_monthly_units": 2, "peak_month": "Forecast", "peak_units": 49492, "revenue_mxn": 37411, "margin_pct": 20418, "py_units": 33659},
    {"sku": "DUO", "canal": "LineName", "avg_monthly_units": 1, "peak_month": "Forecast", "peak_units": 43200, "revenue_mxn": 0, "margin_pct": 9600, "py_units": 0},
    {"sku": "Soul", "canal": "LineName", "avg_monthly_units": 6, "peak_month": "Forecast", "peak_units": 42290, "revenue_mxn": 0, "margin_pct": 420, "py_units": 0},
    {"sku": "Pro", "canal": "LineName", "avg_monthly_units": 4, "peak_month": "Forecast", "peak_units": 25549, "revenue_mxn": 23376, "margin_pct": 14536, "py_units": 15348},
    {"sku": "Mini", "canal": "LineName", "avg_monthly_units": 4, "peak_month": "Forecast", "peak_units": 20106, "revenue_mxn": 6032, "margin_pct": 4313, "py_units": 2532},
]


def auth_error(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def create_token(company: str, username: str) -> str:
    payload = {"company": company, "username": username}
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    signature = hmac.new(APP_SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), "sha256").hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_token(token: str) -> dict:
    try:
        encoded_payload, signature = token.split(".", 1)
    except ValueError as exc:
        raise auth_error() from exc
    expected_signature = hmac.new(APP_SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), "sha256").hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        raise auth_error()
    try:
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload.encode("utf-8")).decode("utf-8"))
    except Exception as exc:  # pragma: no cover - defensive decoding
        raise auth_error() from exc
    if payload.get("username") != COMPANY_USER:
        raise auth_error()
    return payload


def require_company_auth(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise auth_error()
    return verify_token(auth_header.split(" ", 1)[1].strip())


def build_demand_forecast():
    total_forecast = sum(item["final_fcst"] for item in MONTHLY_FORECAST_DATA)
    total_ma = sum(item["ma_fcst"] for item in MONTHLY_FORECAST_DATA)
    total_py = 433503
    peak_month = max(MONTHLY_FORECAST_DATA, key=lambda item: item["final_fcst"])
    month_capacity = [
        {
            "month": "Ene 2026",
            "flag": "YTD",
            "forecast_units": 0,
            "baseline_units": 0,
            "actual_units": 476926,
            "reference_units": 416796,
        },
        {
            "month": "Feb 2026",
            "flag": "YTD",
            "forecast_units": 0,
            "baseline_units": 0,
            "actual_units": 734962,
            "reference_units": 702429,
        },
    ]
    month_capacity.extend(
        {
            "month": item["month"],
            "flag": item["flag"],
            "forecast_units": item["final_fcst"],
            "baseline_units": item["ma_fcst"],
            "actual_units": item["sales_order"],
            "reference_units": item["py"],
        }
        for item in MONTHLY_FORECAST_DATA
    )
    return {
        "company": {
            "name": COMPANY_NAME,
            "country": "Mexico",
            "category": "Healthy snacks & functional foods",
            "note": "Datos agregados desde Forecast Data (1).xlsx con nuevo modelo basado en PartNo, LineName y FlavorVal.",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "units_6m": total_forecast,
            "revenue_6m_mxn": total_py,
            "avg_service_level_pct": 256264,
            "active_skus": 58,
            "peak_month": peak_month["month"],
            "peak_units": peak_month["final_fcst"],
            "capacity_utilization_peak_pct": total_ma,
        },
        "monthly_forecast": [
            {
                "month": item["month"],
                "units": item["final_fcst"],
                "revenue_mxn": item["py"],
                "baseline_units": item["ma_fcst"],
                "upside_units": item["py"],
            }
            for item in MONTHLY_FORECAST_DATA
        ],
        "sku_rows": GROUP_FORECAST_DATA,
        "sku_chart": [],
        "regional_mix": SEGMENTATION_DATA,
        "capacity_plan": month_capacity,
        "alerts": [
            "El nuevo corte 2026 es mucho más acotado: YTD enero-febrero y YTG marzo-junio, con 58 SKU activas.",
            "Mayo es el mayor mes de forecast con 197.476 unidades y supera con holgura al promedio móvil cargado.",
            "El modelo ahora se explica mejor por Market Intelligence y Pure Stat. Fcst, mientras LineName reemplaza al antiguo GroupName.",
        ],
        "assumptions": [
            "Se usó la hoja Export del archivo Forecast Data (1).xlsx compartido por el usuario.",
            "El dataset ahora incluye años 2025 y 2026, pero el módulo se reajustó para mostrar el corte operativo 2026.",
            "Como GroupName ya no viene en el export, el agregado principal se rehizo con LineName y la jerarquía de segmentación del archivo.",
        ],
    }


@app.get("/", response_model=None)
def home():
    if FRONTEND_INDEX.exists():
        return FileResponse(FRONTEND_INDEX)

    return JSONResponse(
        {
        "project": "Red de Cadena de Suministro Chile - México",
        "status": "ok",
        "version": "0.1.0",
        }
    )


@app.get("/eventos", response_model=None)
def eventos():
    if FRONTEND_EVENTOS.exists():
        return FileResponse(FRONTEND_EVENTOS)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/eventos.html",
        },
        status_code=404,
    )


@app.get("/bolsa", response_model=None)
def bolsa():
    if FRONTEND_BOLSA.exists():
        return FileResponse(FRONTEND_BOLSA)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/bolsa.html",
        },
        status_code=404,
    )


@app.get("/publicaciones", response_model=None)
def publicaciones():
    if FRONTEND_PUBLICACIONES.exists():
        return FileResponse(FRONTEND_PUBLICACIONES)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/publicaciones.html",
        },
        status_code=404,
    )


@app.get("/proyeccion", response_model=None)
def proyeccion():
    if FRONTEND_PROYECCION.exists():
        return FileResponse(FRONTEND_PROYECCION)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/proyeccion.html",
        },
        status_code=404,
    )


@app.get("/api")
def root() -> dict:
    return {
        "project": "Red de Cadena de Suministro Chile - México",
        "status": "ok",
        "version": "0.1.0",
    }


@app.post("/api/company-login")
def company_login(payload: CompanyLogin) -> dict:
    company = payload.company.strip() or COMPANY_NAME
    if not hmac.compare_digest(payload.username.strip(), COMPANY_USER):
        raise auth_error("Credenciales invalidas")
    if not hmac.compare_digest(payload.password, COMPANY_PASSWORD):
        raise auth_error("Credenciales invalidas")
    token = create_token(company, payload.username.strip())
    return {
        "token": token,
        "company": company,
        "display_name": COMPANY_NAME,
        "session_id": secrets.token_hex(8),
    }


@app.get("/api/company-me")
def company_me(auth: dict = Depends(require_company_auth)) -> dict:
    return {
        "company": auth.get("company", COMPANY_NAME),
        "username": auth.get("username", COMPANY_USER),
        "display_name": COMPANY_NAME,
    }


@app.get("/api/private/demand-forecast")
def demand_forecast(auth: dict = Depends(require_company_auth)) -> dict:
    forecast = build_demand_forecast()
    forecast["viewer"] = {
        "company": auth.get("company", COMPANY_NAME),
        "username": auth.get("username", COMPANY_USER),
        "display_name": COMPANY_NAME,
    }
    return forecast


@app.get("/nodes")
@app.get("/api/nodes")
def list_nodes() -> list[dict]:
    return NODES


@app.post("/nodes")
@app.post("/api/nodes")
def create_node(node: Node) -> dict:
    NODES.append(node.model_dump())
    return {"message": "Nodo agregado", "node": node}

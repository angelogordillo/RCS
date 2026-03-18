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
    {"month": "Mar 2026", "final_fcst": 644475, "ma_fcst": 574822, "sales_order": 0, "py": 627595, "sku_count": 178, "flag": "YTG"},
    {"month": "Abr 2026", "final_fcst": 559987, "ma_fcst": 574822, "sales_order": 0, "py": 654728, "sku_count": 169, "flag": "YTG"},
    {"month": "May 2026", "final_fcst": 584871, "ma_fcst": 574822, "sales_order": 0, "py": 587989, "sku_count": 170, "flag": "YTG"},
    {"month": "Jun 2026", "final_fcst": 528423, "ma_fcst": 574822, "sales_order": 0, "py": 441467, "sku_count": 166, "flag": "YTG"},
    {"month": "Jul 2026", "final_fcst": 580202, "ma_fcst": 574822, "sales_order": 0, "py": 538751, "sku_count": 166, "flag": "YTG"},
    {"month": "Ago 2026", "final_fcst": 549080, "ma_fcst": 574822, "sales_order": 0, "py": 580783, "sku_count": 166, "flag": "YTG"},
    {"month": "Sep 2026", "final_fcst": 552905, "ma_fcst": 574822, "sales_order": 0, "py": 654959, "sku_count": 166, "flag": "YTG"},
    {"month": "Oct 2026", "final_fcst": 705588, "ma_fcst": 574822, "sales_order": 0, "py": 765746, "sku_count": 166, "flag": "YTG"},
    {"month": "Nov 2026", "final_fcst": 615754, "ma_fcst": 574822, "sales_order": 0, "py": 578993, "sku_count": 168, "flag": "YTG"},
    {"month": "Dic 2026", "final_fcst": 551898, "ma_fcst": 574822, "sales_order": 0, "py": 520727, "sku_count": 166, "flag": "YTG"},
]

SEGMENTATION_DATA = [
    {"region": "Stat. Fcst", "share_pct": 81.0, "units_6m": 4731978},
    {"region": "Pure Stat. Fcst", "share_pct": 13.0, "units_6m": 761799},
    {"region": "Alternative Strategies", "share_pct": 5.4, "units_6m": 316198},
    {"region": "Market Intelligence", "share_pct": 1.1, "units_6m": 63208},
]

GROUP_FORECAST_DATA = [
    {"sku": "WILD PROTEIN", "canal": "Main group", "avg_monthly_units": 76, "peak_month": "Forecast", "peak_units": 4257984, "revenue_mxn": 4298813, "margin_pct": 904392, "py_units": 4849413},
    {"sku": "WILD SOUL", "canal": "Main group", "avg_monthly_units": 16, "peak_month": "Forecast", "peak_units": 854102, "revenue_mxn": 831650, "margin_pct": 191910, "py_units": 1246487},
    {"sku": "WILD FIT", "canal": "Main group", "avg_monthly_units": 14, "peak_month": "Forecast", "peak_units": 574089, "revenue_mxn": 484250, "margin_pct": 84544, "py_units": 637868},
    {"sku": "WILD PROTEIN PRO", "canal": "Main group", "avg_monthly_units": 28, "peak_month": "Forecast", "peak_units": 144200, "revenue_mxn": 116127, "margin_pct": 26605, "py_units": 232992},
    {"sku": "WILD FOODS", "canal": "Main group", "avg_monthly_units": 8, "peak_month": "Forecast", "peak_units": 38486, "revenue_mxn": 14287, "margin_pct": 3736, "py_units": 16966},
    {"sku": "COMPLEMENTO VENTA", "canal": "Main group", "avg_monthly_units": 41, "peak_month": "Forecast", "peak_units": 4322, "revenue_mxn": 3045, "margin_pct": 691, "py_units": 5042},
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
    total_py = sum(item["py"] for item in MONTHLY_FORECAST_DATA)
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
            "note": "Datos agregados desde Forecast Data.xlsx (Export 2026, YTD/YTG, ProductType PTE).",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "units_6m": total_forecast,
            "revenue_6m_mxn": total_py,
            "avg_service_level_pct": 1211888,
            "active_skus": 185,
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
            "El forecast agregado 2026 suma 5.87 millones de unidades contra 7.07 millones del PY visible en el export.",
            "Octubre es el mayor mes de forecast con 705.588 unidades, mientras enero y febrero ya muestran ventas YTD reales.",
            "La mayor parte del volumen proyectado cae en Stat. Fcst con 81% del forecast, seguido por Pure Stat. Fcst con 13%.",
        ],
        "assumptions": [
            "Se usó la hoja Export del archivo Forecast Data.xlsx compartido por el usuario.",
            "Los totales se consolidaron fuera del archivo y se dejaron embebidos en el backend para no depender de la ruta Downloads.",
            "YTD aporta Sales Order en enero-febrero; YTG aporta Final Forecast, MA Forecast y referencia PY de marzo a diciembre.",
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

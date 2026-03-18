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

SIMULATED_WILD_FOODS_SKUS = [
    {"sku": "Protein Bites Cacao 45g", "canal": "Autoservicio", "base": 18500, "precio": 28.5, "margen": 0.34},
    {"sku": "Protein Bites Matcha 45g", "canal": "E-commerce", "base": 9200, "precio": 31.0, "margen": 0.39},
    {"sku": "Granola Clean Label 300g", "canal": "Clubes de precio", "base": 14100, "precio": 74.0, "margen": 0.28},
    {"sku": "Nut Butter Almond 250g", "canal": "Retail especializado", "base": 7600, "precio": 119.0, "margen": 0.32},
    {"sku": "Nut Butter Peanut 400g", "canal": "Autoservicio", "base": 11100, "precio": 96.0, "margen": 0.31},
    {"sku": "Keto Cookies Vanilla 120g", "canal": "E-commerce", "base": 6800, "precio": 65.0, "margen": 0.36},
]

MONTH_LABELS = [
    "Abr 2026",
    "May 2026",
    "Jun 2026",
    "Jul 2026",
    "Ago 2026",
    "Sep 2026",
]

SEASONALITY = [1.0, 1.04, 1.08, 1.12, 1.09, 1.15]
REGIONAL_SPLIT = [
    {"region": "Centro", "share": 0.41},
    {"region": "Norte", "share": 0.24},
    {"region": "Occidente", "share": 0.21},
    {"region": "Sureste", "share": 0.14},
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


def month_total(index: int) -> int:
    base_total = sum(item["base"] for item in SIMULATED_WILD_FOODS_SKUS)
    return round(base_total * SEASONALITY[index])


def build_demand_forecast():
    monthly_units = [month_total(index) for index in range(len(MONTH_LABELS))]
    monthly_revenue = []
    sku_rows = []
    sku_chart = []
    capacity_limit = 76000

    for item in SIMULATED_WILD_FOODS_SKUS:
        sku_monthly = [round(item["base"] * factor) for factor in SEASONALITY]
        monthly_revenue.append(sum(units * item["precio"] for units in sku_monthly))
        sku_rows.append(
            {
                "sku": item["sku"],
                "canal": item["canal"],
                "avg_monthly_units": round(sum(sku_monthly) / len(sku_monthly)),
                "peak_month": MONTH_LABELS[sku_monthly.index(max(sku_monthly))],
                "peak_units": max(sku_monthly),
                "revenue_mxn": round(sum(units * item["precio"] for units in sku_monthly)),
                "margin_pct": round(item["margen"] * 100, 1),
            }
        )
        sku_chart.append(
            {
                "sku": item["sku"],
                "values": sku_monthly,
            }
        )

    regional_mix = []
    for region in REGIONAL_SPLIT:
        demand = round(sum(monthly_units) * region["share"])
        regional_mix.append(
            {
                "region": region["region"],
                "units_6m": demand,
                "share_pct": round(region["share"] * 100, 1),
            }
        )

    month_capacity = []
    for label, units in zip(MONTH_LABELS, monthly_units):
        utilization = round((units / capacity_limit) * 100, 1)
        month_capacity.append(
            {
                "month": label,
                "forecast_units": units,
                "capacity_limit": capacity_limit,
                "utilization_pct": utilization,
                "gap_units": capacity_limit - units,
            }
        )

    total_units = sum(monthly_units)
    return {
        "company": {
            "name": COMPANY_NAME,
            "country": "Mexico",
            "category": "Healthy snacks & functional foods",
            "note": "Datos simulados para demo privada de planeacion de demanda en RCS.",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "units_6m": total_units,
            "revenue_6m_mxn": round(sum(monthly_revenue)),
            "avg_service_level_pct": 96.2,
            "forecast_accuracy_pct": 91.4,
            "peak_month": MONTH_LABELS[monthly_units.index(max(monthly_units))],
            "peak_units": max(monthly_units),
            "capacity_utilization_peak_pct": max(item["utilization_pct"] for item in month_capacity),
        },
        "monthly_forecast": [
            {
                "month": label,
                "units": units,
                "revenue_mxn": round(units * 58.4),
                "baseline_units": round(units * 0.93),
                "upside_units": round(units * 1.12),
            }
            for label, units in zip(MONTH_LABELS, monthly_units)
        ],
        "sku_rows": sku_rows,
        "sku_chart": sku_chart,
        "regional_mix": regional_mix,
        "capacity_plan": month_capacity,
        "alerts": [
            "Agosto y septiembre concentran la mayor presion sobre capacidad por promociones de regreso a rutina.",
            "E-commerce aporta el margen mas alto; conviene proteger inventario de Protein Bites Matcha y Keto Cookies.",
            "Centro y Norte explican 65% de la demanda proyectada, por lo que el stock de seguridad deberia priorizar CDMX y Monterrey.",
        ],
        "assumptions": [
            "Sell-out historico simulado de 6 SKUs con crecimiento estacional moderado.",
            "No se incorporan quiebres de proveedor, FX ni cambios regulatorios.",
            "Capacidad mensual fija para empaque y despacho equivalente a 76 mil unidades.",
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

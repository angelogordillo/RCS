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

SKU_HISTORY = [
    {"month": "2025-01", "fcst_qty": 10185, "order_qty": 16151, "bias_qty": -5966, "error_qty": 5966, "bias_pct": -36.9, "accuracy_pct": 63.1, "fva_pct": 63.1, "fva_units": 10185},
    {"month": "2025-02", "fcst_qty": 7473, "order_qty": 9674, "bias_qty": -2201, "error_qty": 2201, "bias_pct": -22.7, "accuracy_pct": 77.2, "fva_pct": 77.2, "fva_units": 7473},
    {"month": "2025-03", "fcst_qty": 6237, "order_qty": 9472, "bias_qty": -3235, "error_qty": 3235, "bias_pct": -34.2, "accuracy_pct": 65.8, "fva_pct": 65.8, "fva_units": 6237},
    {"month": "2025-04", "fcst_qty": 9786, "order_qty": 9229, "bias_qty": 557, "error_qty": 557, "bias_pct": 6.0, "accuracy_pct": 94.0, "fva_pct": 44.4, "fva_units": 4096},
    {"month": "2025-05", "fcst_qty": 10060, "order_qty": 16008, "bias_qty": -5948, "error_qty": 5948, "bias_pct": -37.2, "accuracy_pct": 62.8, "fva_pct": 5.9, "fva_units": 939},
    {"month": "2025-06", "fcst_qty": 9514, "order_qty": 9221, "bias_qty": 293, "error_qty": 293, "bias_pct": 3.2, "accuracy_pct": 96.8, "fva_pct": 8.6, "fva_units": 794},
    {"month": "2025-07", "fcst_qty": 15580, "order_qty": 14637, "bias_qty": 943, "error_qty": 943, "bias_pct": 6.4, "accuracy_pct": 93.6, "fva_pct": -5.0, "fva_units": -731},
    {"month": "2025-08", "fcst_qty": 11865, "order_qty": 11931, "bias_qty": -66, "error_qty": 66, "bias_pct": -0.6, "accuracy_pct": 99.4, "fva_pct": 15.4, "fva_units": 1833},
    {"month": "2025-09", "fcst_qty": 15094, "order_qty": 15757, "bias_qty": -663, "error_qty": 663, "bias_pct": -4.2, "accuracy_pct": 95.8, "fva_pct": 17.7, "fva_units": 2794},
    {"month": "2025-10", "fcst_qty": 10823, "order_qty": 15173, "bias_qty": -4350, "error_qty": 4350, "bias_pct": -28.7, "accuracy_pct": 71.3, "fva_pct": -12.2, "fva_units": -1847},
    {"month": "2025-11", "fcst_qty": 19732, "order_qty": 15690, "bias_qty": 4042, "error_qty": 4042, "bias_pct": 25.8, "accuracy_pct": 74.2, "fva_pct": -23.1, "fva_units": -3623},
    {"month": "2025-12", "fcst_qty": 23542, "order_qty": 17417, "bias_qty": 6125, "error_qty": 6125, "bias_pct": 35.2, "accuracy_pct": 64.8, "fva_pct": -25.7, "fva_units": -4469},
    {"month": "2026-01", "fcst_qty": 17886, "order_qty": 13935, "bias_qty": 3951, "error_qty": 3951, "bias_pct": 28.4, "accuracy_pct": 71.6, "fva_pct": -19.9, "fva_units": -2768},
    {"month": "2026-02", "fcst_qty": 21149, "order_qty": 13840, "bias_qty": 7309, "error_qty": 7309, "bias_pct": 52.8, "accuracy_pct": 47.2, "fva_pct": -24.5, "fva_units": -3387},
]

SKU_PROFILE = {
    "part_no": "MX0200046031040",
    "part_name": "WP CHOCOLATE 5U",
    "part_no_name": "MX0200046031040 - WP CHOCOLATE 5U",
    "segmentation": "1 - Market Intelligence",
    "demand_pattern": "Erratic",
    "category": "Barras",
    "line_name": "Barras",
    "flavor": "Chocolate",
    "format": "5U",
    "life_cycle": "Active",
    "adj_cv": 0.715,
    "base_fx_sensitivity": 0.45,
    "base_gdp_sensitivity": 0.9,
}

SCENARIO_DEFAULTS = {
    "base_fx": 18.8,
    "expected_fx": 20.2,
    "gdp_growth_pct": 1.8,
    "inflation_pct": 4.2,
    "horizon_months": 6,
}


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
    total_fcst = sum(item["fcst_qty"] for item in SKU_HISTORY)
    total_orders = sum(item["order_qty"] for item in SKU_HISTORY)
    total_error = sum(item["error_qty"] for item in SKU_HISTORY)
    avg_accuracy = round(max(0, (1 - (total_error / total_orders))) * 100, 1) if total_orders else 0.0
    avg_bias = round(((total_fcst - total_orders) / total_orders) * 100, 1) if total_orders else 0.0
    avg_fva = round(sum(item["fva_pct"] for item in SKU_HISTORY) / len(SKU_HISTORY), 1)
    latest = SKU_HISTORY[-1]
    recent_fcst = SKU_HISTORY[-3:]
    base_next_month = round(sum(item["fcst_qty"] for item in recent_fcst) / len(recent_fcst))

    scenario_projection = []
    projected_base = base_next_month
    month_labels = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
    for idx, month in enumerate(month_labels[: SCENARIO_DEFAULTS["horizon_months"]]):
        seasonality = [1.0, 1.04, 1.09, 1.02, 1.01, 0.98][idx]
        scenario_projection.append(
            {
                "month": month,
                "baseline_qty": round(projected_base * seasonality),
            }
        )
    return {
        "company": {
            "name": COMPANY_NAME,
            "country": "Mexico",
            "category": "Healthy snacks & functional foods",
            "note": "Detail SKU dataset aplicado sobre un tablero de escenarios macro para Wild Foods Mexico.",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "units_6m": total_fcst,
            "revenue_6m_mxn": total_orders,
            "avg_service_level_pct": avg_accuracy,
            "active_skus": 1,
            "peak_month": latest["month"],
            "peak_units": latest["fcst_qty"],
            "capacity_utilization_peak_pct": avg_bias,
        },
        "monthly_forecast": [
            {
                "month": item["month"],
                "units": item["fcst_qty"],
                "revenue_mxn": item["order_qty"],
                "baseline_units": item["order_qty"],
                "upside_units": max(item["fcst_qty"], item["order_qty"]),
            }
            for item in SKU_HISTORY
        ],
        "sku_rows": [
            {
                "sku": SKU_PROFILE["part_name"],
                "part_no": SKU_PROFILE["part_no"],
                "segmentation": SKU_PROFILE["segmentation"],
                "pattern": SKU_PROFILE["demand_pattern"],
                "category": SKU_PROFILE["category"],
                "line_name": SKU_PROFILE["line_name"],
                "flavor": SKU_PROFILE["flavor"],
                "format": SKU_PROFILE["format"],
                "life_cycle": SKU_PROFILE["life_cycle"],
                "adj_cv": SKU_PROFILE["adj_cv"],
                "months": len(SKU_HISTORY),
                "base_fcst": total_fcst,
                "base_orders": total_orders,
                "bias_qty": total_fcst - total_orders,
                "error_qty": total_error,
                "bias_pct": avg_bias,
                "accuracy_pct": avg_accuracy,
                "fva_units": round(sum(item["fva_units"] for item in SKU_HISTORY)),
                "fx_sensitivity": SKU_PROFILE["base_fx_sensitivity"],
                "gdp_sensitivity": SKU_PROFILE["base_gdp_sensitivity"],
            }
        ],
        "sku_chart": SKU_HISTORY,
        "regional_mix": [],
        "capacity_plan": [],
        "scenario_defaults": SCENARIO_DEFAULTS,
        "scenario_projection": scenario_projection,
        "sku_profile": SKU_PROFILE,
        "alerts": [
            "El SKU muestra alta volatilidad: el Adj CV es 0.715 y el patrón de demanda está marcado como Erratic.",
            "El último corte disponible, febrero 2026, cerró con accuracy de 47.2% y sesgo positivo de 52.8%.",
            "El modelo de escenario usa sensibilidad de tipo de cambio y PIB para proyectar los siguientes 6 meses del SKU.",
        ],
        "assumptions": [
            "Se usó Detail.xlsx compartido por el usuario; el archivo contiene una serie histórica mensual para el SKU MX0200046031040.",
            "La proyección base futura parte del promedio de los últimos 3 meses de forecast observados.",
            "Los drivers macro afectan la proyección con elasticidades simples: FX 0.45 y PIB 0.9 sobre la base del SKU.",
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

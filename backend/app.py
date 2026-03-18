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

REAL_FORECAST_MONTHS = [
    {"month": "2025-1", "forecast_qty": 429000, "order_qty": 417000, "bias_pct": 3, "accuracy_pct": 76},
    {"month": "2025-2", "forecast_qty": 664000, "order_qty": 702000, "bias_pct": -5, "accuracy_pct": 84},
    {"month": "2025-3", "forecast_qty": 643000, "order_qty": 624000, "bias_pct": 3, "accuracy_pct": 71},
    {"month": "2025-4", "forecast_qty": 505000, "order_qty": 655000, "bias_pct": -23, "accuracy_pct": 69},
    {"month": "2025-5", "forecast_qty": 462000, "order_qty": 588000, "bias_pct": -21, "accuracy_pct": 73},
    {"month": "2025-6", "forecast_qty": 542000, "order_qty": 484000, "bias_pct": 12, "accuracy_pct": 74},
    {"month": "2025-7", "forecast_qty": 542000, "order_qty": 536000, "bias_pct": 1, "accuracy_pct": 70},
    {"month": "2025-8", "forecast_qty": 542000, "order_qty": 581000, "bias_pct": -7, "accuracy_pct": 81},
    {"month": "2025-9", "forecast_qty": 536000, "order_qty": 655000, "bias_pct": -18, "accuracy_pct": 66},
    {"month": "2025-10", "forecast_qty": 619000, "order_qty": 766000, "bias_pct": -19, "accuracy_pct": 74},
    {"month": "2025-11", "forecast_qty": 548000, "order_qty": 576000, "bias_pct": -5, "accuracy_pct": 80},
    {"month": "2025-12", "forecast_qty": 461472, "order_qty": 520727, "bias_pct": -11, "accuracy_pct": 76, "fva_pct": 9, "fva_units": 45588},
]

FORECAST_GROUPS = [
    {"segment": "1 - Market Intelligence", "products": 3, "avg_fcst_qty": 9057, "avg_order_qty": 9623, "avg_bias_qty": -567, "avg_error_qty": 4067, "bias_pct": -6, "accuracy_pct": 58, "fva_pct": 27, "avg_fva_units": 2564},
    {"segment": "2 - Stat. Fcst", "products": 36, "avg_fcst_qty": 423554, "avg_order_qty": 462344, "avg_bias_qty": -38790, "avg_error_qty": 101085, "bias_pct": -8, "accuracy_pct": 78, "fva_pct": 37, "avg_fva_units": 172147},
    {"segment": "3 - Pure Stat. Fcst", "products": 86, "avg_fcst_qty": 78837, "avg_order_qty": 83808, "avg_bias_qty": -4971, "avg_error_qty": 26376, "bias_pct": -6, "accuracy_pct": 69, "fva_pct": 35, "avg_fva_units": 29003},
    {"segment": "4 - Alternative Strat.", "products": 52, "avg_fcst_qty": 25853, "avg_order_qty": 33472, "avg_bias_qty": -7619, "avg_error_qty": 16856, "bias_pct": -23, "accuracy_pct": 50, "fva_pct": 37, "avg_fva_units": 12219},
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
    monthly_rows = []
    for row in REAL_FORECAST_MONTHS:
        forecast_qty = row["forecast_qty"]
        order_qty = row["order_qty"]
        bias_qty = forecast_qty - order_qty
        error_qty = abs(bias_qty)
        fva_units = row.get("fva_units", round(error_qty * 0.37))
        monthly_rows.append(
            {
                "month": row["month"],
                "forecast_qty": forecast_qty,
                "order_qty": order_qty,
                "bias_qty": bias_qty,
                "error_qty": error_qty,
                "bias_pct": row["bias_pct"],
                "accuracy_pct": row["accuracy_pct"],
                "fva_pct": row.get("fva_pct", 37),
                "fva_units": fva_units,
            }
        )

    best_accuracy = max(monthly_rows, key=lambda item: item["accuracy_pct"])
    worst_bias = min(monthly_rows, key=lambda item: item["bias_pct"])
    peak_order = max(monthly_rows, key=lambda item: item["order_qty"])

    return {
        "company": {
            "name": COMPANY_NAME,
            "country": "Mexico",
            "category": "Healthy snacks & functional foods",
            "note": "Benchmark 2025 incorporado desde tablero operativo de forecasting compartido por el cliente.",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "total_products": 177,
            "avg_bias_pct": -9,
            "avg_accuracy_pct": 75,
            "avg_fva_pct": 37,
            "mtd_bias_pct": -11,
            "mtd_accuracy_pct": 76,
            "mtd_fva_pct": 9,
            "peak_month": peak_order["month"],
            "peak_order_qty": peak_order["order_qty"],
            "best_accuracy_month": best_accuracy["month"],
            "best_accuracy_pct": best_accuracy["accuracy_pct"],
            "worst_bias_month": worst_bias["month"],
            "worst_bias_pct": worst_bias["bias_pct"],
        },
        "monthly_kpis": monthly_rows,
        "group_rows": FORECAST_GROUPS,
        "alerts": [
            "Abril, mayo y octubre concentran los peores sesgos de forecast, todos con subforecast superior a -19%.",
            "Febrero y agosto muestran los mejores niveles de accuracy con 84% y 81% respectivamente.",
            "Diciembre mantiene sesgo negativo de -11% y FVA MTD de 9%, señal de oportunidad para mejorar el proceso colaborativo.",
        ],
        "assumptions": [
            "La base se reconstruyó desde la captura del tablero de Forecasting KPIs compartida por el usuario.",
            "Los valores de accuracy de 2025-9 y 2025-11 se estimaron visualmente porque la captura no mostraba la etiqueta completa.",
            "Los volúmenes mensuales siguen el patrón visible en la gráfica de Forecast vs Order; no se incorporaron más dimensiones fuera de la imagen.",
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

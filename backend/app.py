from pathlib import Path
from datetime import date, datetime
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
FRONTEND_SEMINARIO = BASE_DIR / "frontend" / "seminario.html"
FRONTEND_ADMIN = BASE_DIR / "frontend" / "adm.html"
FRONTEND_BOLSA = BASE_DIR / "frontend" / "bolsa.html"
FRONTEND_PUBLICACIONES = BASE_DIR / "frontend" / "publicaciones.html"
FRONTEND_PROYECCION = BASE_DIR / "frontend" / "proyeccion.html"
LOGOS_DIR = BASE_DIR / "logos"
DATA_DIR = BASE_DIR / "data"
SEMINARIO_WAITLIST_FILE = DATA_DIR / "seminario_waitlist.ndjson"
COMPANY_USER = os.getenv("RCS_COMPANY_USER", "wildfoods")
COMPANY_PASSWORD = os.getenv("RCS_COMPANY_PASSWORD", "wildfoods2026")
COMPANY_NAME = os.getenv("RCS_COMPANY_NAME", "Wild Foods Mexico")
ADMIN_USER = os.getenv("RCS_ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("RCS_ADMIN_PASSWORD", "rcs2026")
ADMIN_NAME = os.getenv("RCS_ADMIN_NAME", "Administrador RCS")
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


class AdminLogin(BaseModel):
    username: str
    password: str


class SeminarioWaitlistEntry(BaseModel):
    nombre: str
    email: str
    empresa: str
    cargo: str
    pais: str
    interes: str | None = ""


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

PROJECTION_DEFAULTS = {
    "horizon_months": 12,
    "blend_actual_weight": 0.65,
    "blend_forecast_weight": 0.35,
}


def auth_error(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def create_token(username: str, role: str, company: str = "") -> str:
    payload = {"company": company, "username": username, "role": role}
    encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
    signature = hmac.new(APP_SECRET.encode("utf-8"), encoded_payload.encode("utf-8"), "sha256").hexdigest()
    return f"{encoded_payload}.{signature}"


def verify_token(token: str, expected_role: str | None = None, expected_username: str | None = None) -> dict:
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
    if expected_role and payload.get("role") != expected_role:
        raise auth_error()
    if expected_username and payload.get("username") != expected_username:
        raise auth_error()
    return payload


def require_company_auth(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise auth_error()
    return verify_token(auth_header.split(" ", 1)[1].strip(), expected_role="company", expected_username=COMPANY_USER)


def require_admin_auth(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise auth_error()
    return verify_token(auth_header.split(" ", 1)[1].strip(), expected_role="admin", expected_username=ADMIN_USER)


def build_demand_forecast():
    total_fcst = sum(item["fcst_qty"] for item in SKU_HISTORY)
    total_orders = sum(item["order_qty"] for item in SKU_HISTORY)
    total_error = sum(item["error_qty"] for item in SKU_HISTORY)
    avg_accuracy = round(max(0, (1 - (total_error / total_orders))) * 100, 1) if total_orders else 0.0
    avg_bias = round(((total_fcst - total_orders) / total_orders) * 100, 1) if total_orders else 0.0
    avg_fva = round(sum(item["fva_pct"] for item in SKU_HISTORY) / len(SKU_HISTORY), 1)
    latest = SKU_HISTORY[-1]
    best_month = max(SKU_HISTORY, key=lambda item: item["accuracy_pct"])
    worst_month = min(SKU_HISTORY, key=lambda item: item["accuracy_pct"])
    recent_window = SKU_HISTORY[-6:]
    recent_orders = round(sum(item["order_qty"] for item in recent_window) / len(recent_window))
    recent_fcst = round(sum(item["fcst_qty"] for item in recent_window) / len(recent_window))
    base_projection = round(
        (recent_orders * PROJECTION_DEFAULTS["blend_actual_weight"])
        + (recent_fcst * PROJECTION_DEFAULTS["blend_forecast_weight"])
    )
    seasonality_curve = [0.94, 0.97, 1.02, 1.05, 1.08, 1.1, 1.07, 1.03, 0.99, 0.96, 0.95, 0.98]
    projection_months = [
        "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
        "2026-09", "2026-10", "2026-11", "2026-12", "2027-01", "2027-02",
    ]
    annual_projection = []
    for idx, month in enumerate(projection_months[: PROJECTION_DEFAULTS["horizon_months"]]):
        seasonality = seasonality_curve[idx]
        projected_units = round(base_projection * seasonality)
        annual_projection.append(
            {
                "month": month,
                "projected_units": projected_units,
                "vs_recent_avg_pct": round(((projected_units - recent_orders) / recent_orders) * 100, 1) if recent_orders else 0.0,
            }
        )

    projection_total = sum(item["projected_units"] for item in annual_projection)
    annualized_run_rate = round(recent_orders * 12)
    projection_gap_pct = round(((projection_total - annualized_run_rate) / annualized_run_rate) * 100, 1) if annualized_run_rate else 0.0
    closing_gap_units = latest["fcst_qty"] - latest["order_qty"]
    return {
        "company": {
            "name": COMPANY_NAME,
            "country": "Mexico",
            "category": "Healthy snacks & functional foods",
            "note": "Analisis ejecutivo del comportamiento real del SKU frente al pronostico y su proyeccion anualizada.",
        },
        "generated_at": date.today().isoformat(),
        "summary": {
            "forecast_units": total_fcst,
            "actual_units": total_orders,
            "gap_units": total_fcst - total_orders,
            "gap_pct": avg_bias,
            "accuracy_pct": avg_accuracy,
            "fva_pct": avg_fva,
            "best_month": best_month["month"],
            "best_accuracy_pct": best_month["accuracy_pct"],
            "worst_month": worst_month["month"],
            "worst_accuracy_pct": worst_month["accuracy_pct"],
            "latest_month": latest["month"],
            "latest_forecast_units": latest["fcst_qty"],
            "latest_actual_units": latest["order_qty"],
            "latest_gap_units": closing_gap_units,
            "projected_12m_units": projection_total,
            "projected_vs_run_rate_pct": projection_gap_pct,
        },
        "monthly_forecast": [
            {
                "month": item["month"],
                "forecast_units": item["fcst_qty"],
                "actual_units": item["order_qty"],
                "bias_units": item["bias_qty"],
                "accuracy_pct": item["accuracy_pct"],
            }
            for item in SKU_HISTORY
        ],
        "projection_12m": annual_projection,
        "sku_profile": SKU_PROFILE,
        "executive_analysis": [
            f"En el historico disponible el pronostico acumulado supera la venta real por {total_fcst - total_orders:,} unidades, equivalente a un sesgo promedio de {avg_bias}%.".replace(",", "."),
            f"El mejor ajuste del modelo se observo en {best_month['month']} con accuracy de {best_month['accuracy_pct']}%, mientras que {worst_month['month']} fue el punto mas debil con {worst_month['accuracy_pct']}%.".replace(",", "."),
            f"Para el ultimo corte ({latest['month']}), el forecast quedo {closing_gap_units:,} unidades por encima de la venta real; la proyeccion a 12 meses queda en {projection_total:,} unidades.".replace(",", "."),
        ],
        "product_insights": [
            "La propuesta de valor del SKU esta centrada en 15 g de proteina por barra, lo que lo posiciona mas cerca de consumo funcional que de indulgencia pura.",
            "El claim de sin azucar anadida y la comunicacion de bajo sodio y colesterol sugieren que la recompra puede depender de confianza nutricional y no solo de precio o sabor.",
            "El formato de 5 unidades ayuda a explicar una demanda potencialmente mas concentrada en reposiciones por caja o multipack, con picos mas marcados que un SKU de compra unitaria.",
            "La presencia de soya, leche y cacahuate como componentes relevantes sugiere sensibilidad a restricciones por alergenos, por lo que parte de la variabilidad comercial puede venir del universo acotado de consumidores.",
            "Inferencia: al estar presentado como snack con proteina para mantenerte en movimiento, la demanda probablemente responde mejor a activaciones en bienestar, deporte y conveniencia que a una comunicacion genérica de snack.",
        ],
        "alerts": [
            "El SKU mantiene una volatilidad alta y comportamiento erratico, con dispersion relevante entre forecast y venta real.",
            "La precision historica se deteriora de forma visible en el cierre mas reciente, especialmente en enero y febrero de 2026.",
            "La proyeccion de 12 meses se ancla en la venta reciente y suaviza el exceso de optimismo observado en el forecast historico.",
        ],
        "assumptions": [
            "Se usó Detail.xlsx compartido por el usuario; el archivo contiene una serie histórica mensual para el SKU MX0200046031040.",
            "La proyeccion a 12 meses usa una base mixta entre venta real reciente y forecast reciente, con una curva simple de estacionalidad.",
            "El objetivo del modulo es mostrar lectura ejecutiva y no simulacion editable de supuestos.",
            "Los insights complementarios del producto se apoyan en la ficha oficial publicada por Wild Foods Mexico para Wild Protein Chocolate 5 unidades.",
        ],
    }


def save_seminario_waitlist(entry: SeminarioWaitlistEntry) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    record = entry.model_dump()
    record["submitted_at"] = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    with SEMINARIO_WAITLIST_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_seminario_waitlist() -> list[dict]:
    if not SEMINARIO_WAITLIST_FILE.exists():
        return []

    entries: list[dict] = []
    with SEMINARIO_WAITLIST_FILE.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    entries.sort(key=lambda item: item.get("submitted_at", ""), reverse=True)
    return entries


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


@app.get("/eventos/seminario", response_model=None)
def eventos_seminario():
    if FRONTEND_SEMINARIO.exists():
        return FileResponse(FRONTEND_SEMINARIO)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/seminario.html",
        },
        status_code=404,
    )


@app.get("/adm", response_model=None)
def admin():
    if FRONTEND_ADMIN.exists():
        return FileResponse(FRONTEND_ADMIN)

    return JSONResponse(
        {
            "project": "Red de Cadena de Suministro Chile - México",
            "status": "error",
            "message": "No se encontró frontend/adm.html",
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


@app.post("/api/eventos/seminario/waiting-list")
def seminario_waiting_list(payload: SeminarioWaitlistEntry) -> dict:
    payload.email = payload.email.strip()
    if "@" not in payload.email or "." not in payload.email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Correo electrónico inválido")

    payload.nombre = payload.nombre.strip()
    payload.empresa = payload.empresa.strip()
    payload.cargo = payload.cargo.strip()
    payload.pais = payload.pais.strip()
    payload.interes = (payload.interes or "").strip()
    if not all([payload.nombre, payload.empresa, payload.cargo, payload.pais]):
        raise HTTPException(status_code=422, detail="Completa todos los campos obligatorios")

    save_seminario_waitlist(payload)
    return {
        "status": "ok",
        "message": "Tu registro fue agregado al waiting list del seminario.",
    }


@app.post("/api/admin-login")
def admin_login(payload: AdminLogin) -> dict:
    username = payload.username.strip()
    if not hmac.compare_digest(username, ADMIN_USER):
        raise auth_error("Credenciales invalidas")
    if not hmac.compare_digest(payload.password, ADMIN_PASSWORD):
        raise auth_error("Credenciales invalidas")
    token = create_token(username=username, role="admin")
    return {
        "token": token,
        "username": username,
        "display_name": ADMIN_NAME,
        "session_id": secrets.token_hex(8),
    }


@app.post("/api/company-login")
def company_login(payload: CompanyLogin) -> dict:
    company = payload.company.strip() or COMPANY_NAME
    if not hmac.compare_digest(payload.username.strip(), COMPANY_USER):
        raise auth_error("Credenciales invalidas")
    if not hmac.compare_digest(payload.password, COMPANY_PASSWORD):
        raise auth_error("Credenciales invalidas")
    token = create_token(username=payload.username.strip(), role="company", company=company)
    return {
        "token": token,
        "company": company,
        "display_name": COMPANY_NAME,
        "session_id": secrets.token_hex(8),
    }


@app.get("/api/admin-me")
def admin_me(auth: dict = Depends(require_admin_auth)) -> dict:
    return {
        "username": auth.get("username", ADMIN_USER),
        "display_name": ADMIN_NAME,
        "role": auth.get("role", "admin"),
    }


@app.get("/api/private/seminario-waitlist")
def admin_waitlist(auth: dict = Depends(require_admin_auth)) -> dict:
    entries = load_seminario_waitlist()
    return {
        "viewer": {
            "username": auth.get("username", ADMIN_USER),
            "display_name": ADMIN_NAME,
        },
        "summary": {
            "total": len(entries),
            "latest_at": entries[0].get("submitted_at") if entries else None,
        },
        "entries": entries,
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

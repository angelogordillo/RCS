from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RCS API", version="0.1.0")


class Node(BaseModel):
    id: str
    nombre: str
    tipo: str
    estado: str
    capacidad: float


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


@app.get("/")
def root() -> dict:
    return {
        "project": "Red de Cadena de Suministro México",
        "status": "ok",
        "version": "0.1.0",
    }


@app.get("/nodes")
def list_nodes() -> list[dict]:
    return NODES


@app.post("/nodes")
def create_node(node: Node) -> dict:
    NODES.append(node.model_dump())
    return {"message": "Nodo agregado", "node": node}

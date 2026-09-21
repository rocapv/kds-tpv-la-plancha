"""Preparación de las pruebas.

Las pruebas NO tocan la base de datos real: se crea `kds_tpv_test` desde el mismo SQL que
usa producción, se llena con los datos de ejemplo y se destruye al terminar. Así una prueba
no puede estropear un servicio en marcha ni depender de lo que haya vendido el local hoy.
"""
import os
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
BD_PRUEBAS = os.getenv("KDS_TEST_DB", "kds_tpv_test")
SOCKET = os.getenv("KDS_DB_SOCKET", str(Path.home() / ".local/share/kds-mariadb/kds.sock"))


def mariadb(*args, entrada=None):
    return subprocess.run(["mariadb", f"--socket={SOCKET}", "--skip-ssl", *args],
                          input=entrada, capture_output=True, text=True, check=True)


@pytest.fixture(scope="session", autouse=True)
def base_de_pruebas():
    mariadb("-e", f"DROP DATABASE IF EXISTS `{BD_PRUEBAS}`; "
                  f"CREATE DATABASE `{BD_PRUEBAS}` CHARACTER SET utf8mb4 COLLATE utf8mb4_spanish_ci")
    for guion in sorted((RAIZ / "sql").glob("*.sql")):
        mariadb(BD_PRUEBAS, entrada=guion.read_text(encoding="utf-8"))
    os.environ["KDS_DB_NAME"] = BD_PRUEBAS
    os.environ["KDS_DB_SOCKET"] = SOCKET
    # el usuario del sistema entra por socket; en un servidor con root sería el usuario 'kds'
    os.environ.setdefault("KDS_DB_USER", os.getenv("USER") or "kds")
    # El cliente de pruebas no tiene IP: se presenta como "testclient" y la guarda de red
    # lo rechazaría. Se permite solo aquí, nunca en el servicio real.
    os.environ["KDS_HOSTS"] = "testclient"
    yield
    mariadb("-e", f"DROP DATABASE `{BD_PRUEBAS}`")


@pytest.fixture(scope="session")
def cliente(base_de_pruebas):
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c


def _token(cliente, pin):
    r = cliente.post("/api/login", json={"pin": pin})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


@pytest.fixture
def camarero(cliente):
    return _token(cliente, "1111")


@pytest.fixture
def cocina(cliente):
    return _token(cliente, "3333")


@pytest.fixture
def encargado(cliente):
    return _token(cliente, "9999")


def mesa_libre(cliente, camarero):
    """Una mesa sin pedido abierto. Si no queda ninguna, el mensaje lo dice claro:
    es señal de que alguna prueba se ha dejado un pedido abierto."""
    mesas = cliente.get("/api/mesas", headers=camarero).json()
    libres = [m for m in mesas if not m["pedido_id"]]
    assert libres, "no quedan mesas libres: alguna prueba no ha cerrado su pedido"
    return libres[0]


@pytest.fixture
def pedido_enviado(cliente, camarero):
    """Pedido con dos líneas ya en cocina: el estado desde el que se cobra.

    Al terminar la prueba se anula si sigue abierto, para devolver la mesa. Sin esto, las
    pruebas se pisan entre ellas y la número treinta y tantos se queda sin sitio donde sentar.
    """
    pid = cliente.post("/api/pedidos", headers=camarero,
                       json={"tipo": "sala", "mesa_id": mesa_libre(cliente, camarero)["id"]}).json()["id"]
    for producto, cantidad in ((2, 2), (15, 1)):
        cliente.post(f"/api/pedidos/{pid}/lineas", headers=camarero,
                     json={"producto_id": producto, "cantidad": cantidad})
    cliente.post(f"/api/pedidos/{pid}/enviar", headers=camarero)
    yield pid
    if cliente.get(f"/api/pedidos/{pid}", headers=camarero).json()["estado"] == "abierto":
        cliente.post(f"/api/pedidos/{pid}/anular", headers=camarero)

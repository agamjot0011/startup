import os
import sys

# Ensure the backend's site-packages is at the front of sys.path
# so it's picked up before the hermes-agent environment
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_site_packages = os.path.join(backend_dir, 'venv', 'Lib', 'site-packages')
if backend_site_packages not in sys.path:
    sys.path.insert(0, backend_site_packages)

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture
def client():
    return client


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_live_health():
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_ready_health():
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

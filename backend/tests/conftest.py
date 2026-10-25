import os
import pytest
from httpx import AsyncClient, ASGITransport

# Configure environment before importing app
os.environ["ENVIRONMENT"] = "development"
os.environ["DEMO_MODE"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["LLM_API_KEY"] = ""

from app.core.config import settings
from app.core.database import init_db
from app.core.security import create_demo_token
from app.main import create_app


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()
    yield


@pytest.fixture
async def client():
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def viewer_token():
    return create_demo_token(user_id="test-viewer", role="viewer")


@pytest.fixture
def operator_token():
    return create_demo_token(user_id="test-operator", role="operator")


@pytest.fixture
def admin_token():
    return create_demo_token(user_id="test-admin", role="admin")


@pytest.fixture
def viewer_headers(viewer_token):
    return {"Authorization": f"Bearer {viewer_token}"}


@pytest.fixture
def operator_headers(operator_token):
    return {"Authorization": f"Bearer {operator_token}"}


@pytest.fixture
def admin_headers(admin_token):
    return {"Authorization": f"Bearer {admin_token}"}


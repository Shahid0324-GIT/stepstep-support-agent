from fastapi.testclient import TestClient

from app.api.routes import get_agent
from app.main import app


class FakeSupportAgent:
    def chat(
        self,
        message: str,
        context,
    ) -> str:
        return (
            f"Fake response for customer "
            f"{context.customer_id}: {message}"
        )


fake_agent = FakeSupportAgent()

app.dependency_overrides[get_agent] = lambda: fake_agent

client = TestClient(app)


def test_health_check():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_chat_returns_agent_response():
    response = client.post(
        "/api/v1/chat",
        json={
            "customer_id": "CUST-001",
            "message": "Can I cancel ORD-1001?",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert "request_id" in body
    assert body["request_id"].startswith("req-")

    assert (
        body["response"]
        == "Fake response for customer CUST-001: "
        "Can I cancel ORD-1001?"
    )


def test_chat_rejects_missing_customer_id():
    response = client.post(
        "/api/v1/chat",
        json={
            "message": "Can I cancel ORD-1001?",
        },
    )

    assert response.status_code == 422


def test_chat_rejects_empty_message():
    response = client.post(
        "/api/v1/chat",
        json={
            "customer_id": "CUST-001",
            "message": "",
        },
    )

    assert response.status_code == 422
    
def teardown_module():
    app.dependency_overrides.clear()
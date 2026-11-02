
import pytest

from backend.app import app


@pytest.fixture()
def client():
    app.config["TESTING"] = True

    with app.test_client() as test_client:
        yield test_client


def test_home_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "running"
    assert data["eligible_products"] == 104


def test_health_endpoint(client):
    response = client.get("/api/health")

    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["eligible_products"] == 104
    assert data["model"]


def test_categories_endpoint(client):
    response = client.get("/api/categories")

    assert response.status_code == 200

    data = response.get_json()
    assert "categories" in data
    assert len(data["categories"]) > 0


def test_recommend_endpoint(client):
    response = client.get(
        "/api/recommend?q=Diwali%20gifts&limit=5"
    )

    assert response.status_code == 200

    data = response.get_json()
    assert data["query"] == "Diwali gifts"
    assert data["count"] == 5
    assert len(data["results"]) == 5


def test_recommend_without_query(client):
    response = client.get("/api/recommend")

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_recommend_with_price_filter(client):
    response = client.get(
        "/api/recommend?q=birthday%20gift&max_price=1000"
    )

    assert response.status_code == 200

    data = response.get_json()
    assert all(
        product["price"] <= 1000
        for product in data["results"]
    )


def test_negative_price_is_rejected(client):
    response = client.get(
        "/api/recommend?q=birthday%20gift&min_price=-100"
    )

    assert response.status_code == 400
    assert "error" in response.get_json()


def test_invalid_price_value_is_rejected(client):
    response = client.get(
        "/api/recommend?q=birthday%20gift&min_price=abc"
    )

    assert response.status_code == 400
    assert "error" in response.get_json()

from starlette.testclient import TestClient

from app.utils.auth import create_access_token
from main import app

client = TestClient(app)

ALGORITHM = "HS256"


# Тест для проверки доступа с валидным токеном
def test_get_readers_with_token():
    data = {"sub": "1"}
    token = create_access_token(data)
    response = client.get("/readers", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# Тест для проверки доступа без токена
def test_get_readers_without_token():
    response = client.get("/readers")
    assert response.status_code == 401

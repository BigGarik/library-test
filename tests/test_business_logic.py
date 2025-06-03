import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book


@pytest.fixture
async def auth_token(async_client: AsyncClient):
    """Фикстура для получения access токена"""
    await async_client.post("/auth/register", json={"email": "user@example.com", "password": "password123"})
    response = await async_client.post("/auth/login", data={"username": "user@example.com", "password": "password123"})
    return response.json()["access_token"]


@pytest.fixture
async def create_books(db_session: AsyncSession):
    """Создание тестовых книг"""
    books = [
        Book(title="Book 1", author="Author", year=2020, isbn="111", copies=1),
        Book(title="Book 2", author="Author", year=2020, isbn="222", copies=1),
        Book(title="Book 3", author="Author", year=2020, isbn="333", copies=1),
        Book(title="Book 4", author="Author", year=2020, isbn="444", copies=1),
    ]
    db_session.add_all(books)
    await db_session.commit()


@pytest.mark.asyncio
async def test_borrow_limit(async_client: AsyncClient, auth_token, create_books):
    """Нельзя взять более 3 книг одновременно"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    for i in range(3):
        response = await async_client.post(f"/circulation/borrow/{i + 1}", headers=headers)
        assert response.status_code == 200

    response = await async_client.post("/circulation/borrow/4", headers=headers)
    assert response.status_code == 400
    assert "максимум 3 книги" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_borrow_unavailable_book(async_client: AsyncClient, auth_token, db_session: AsyncSession):
    """Нельзя взять книгу, если нет доступных копий"""
    # Предположим, книга с ID 1 уже выдана
    headers = {"Authorization": f"Bearer {auth_token}"}
    await async_client.post("/circulation/borrow/1", headers=headers)

    # Попытка взять ту же книгу снова
    response = await async_client.post("/circulation/borrow/1", headers=headers)
    assert response.status_code == 400
    assert "нет доступных копий" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(async_client: AsyncClient):
    """Без токена доступ запрещён"""
    response = await async_client.get("/books/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_with_auth(async_client: AsyncClient, auth_token):
    """С токеном доступ разрешён"""
    headers = {"Authorization": f"Bearer {auth_token}"}
    response = await async_client.get("/books/1", headers=headers)
    assert response.status_code == 200

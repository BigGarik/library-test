import pytest
import pytest_asyncio

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.database.database import Base
from app.utils.dependencies import get_db
from main import app

DATABASE_URL_TEST = "sqlite+aiosqlite:///:memory:"

engine_test = create_async_engine(DATABASE_URL_TEST, echo=False)
AsyncSessionTest = async_sessionmaker(bind=engine_test, expire_on_commit=False)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
async def prepare_database():
    """Создает таблицы в тестовой БД один раз за сессию"""
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture()
async def db_session() -> AsyncSession:
    """Тестовая сессия SQLAlchemy"""
    async with AsyncSessionTest() as session:
        yield session
        await session.rollback()


@pytest.fixture()
async def async_client(db_session: AsyncSession) -> AsyncClient:
    """HTTP-клиент с тестовой БД"""
    # Подменяем зависимость get_db на фикстуру
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()

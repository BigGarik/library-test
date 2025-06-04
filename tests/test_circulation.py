from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.borrowed_book import BorrowedBook
from app.models.reader import Reader
from app.schemas.borrow import BorrowCreate
from app.services.circulation import (
    check_book_exists,
    check_reader_exists,
    check_book_availability,
    check_borrow_limit,
    create_borrow_record,
    check_borrow_record,
    return_borrowed_book,
    get_active_borrows
)


@pytest_asyncio.fixture
async def mock_db():
    """Фикстура для создания мок-объекта AsyncSession."""
    db = AsyncMock(spec=AsyncSession)
    db.add = MagicMock()  # Заменяем AsyncMock на MagicMock для db.add
    return db


@pytest.mark.asyncio
async def test_check_book_exists_success(mock_db):
    """Тестирует успешную проверку существования книги."""
    mock_book = MagicMock(spec=Book, id=1, copies=1)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: mock_book)

    result = await check_book_exists(mock_db, book_id=1)
    assert result == mock_book
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_book_exists_not_found(mock_db):
    """Тестирует случай, когда книга не найдена."""
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    with pytest.raises(HTTPException) as exc:
        await check_book_exists(mock_db, book_id=999)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Книга не найдена"


@pytest.mark.asyncio
async def test_check_reader_exists_success(mock_db):
    """Тестирует успешную проверку существования читателя."""
    mock_reader = MagicMock(spec=Reader, id=1)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: mock_reader)

    result = await check_reader_exists(mock_db, reader_id=1)
    assert result == mock_reader
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_reader_exists_not_found(mock_db):
    """Тестирует случай, когда читатель не найден."""
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    with pytest.raises(HTTPException) as exc:
        await check_reader_exists(mock_db, reader_id=999)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Читатель не найден"


@pytest.mark.asyncio
async def test_check_book_availability_success():
    """Тестирует успешную проверку доступности книги."""
    mock_book = MagicMock(spec=Book, copies=1)

    await check_book_availability(mock_book)  # Не должно вызывать исключений


@pytest.mark.asyncio
async def test_check_book_availability_no_copies():
    """Тестирует случай, когда нет доступных экземпляров."""
    mock_book = MagicMock(spec=Book, copies=0)

    with pytest.raises(HTTPException) as exc:
        await check_book_availability(mock_book)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Нет доступных экземпляров книги"


@pytest.mark.asyncio
async def test_check_borrow_limit_success(mock_db):
    """Тестирует успешную проверку лимита в 3 книги."""
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [MagicMock()]))

    await check_borrow_limit(mock_db, reader_id=1)  # Не должно вызывать исключений
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_borrow_limit_exceeded(mock_db):
    """Тестирует превышение лимита в 3 книги."""
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [MagicMock() for _ in range(3)]))

    with pytest.raises(HTTPException) as exc:
        await check_borrow_limit(mock_db, reader_id=1)
    assert exc.value.status_code == 400
    assert exc.value.detail == "Читатель не может взять более 3 книг одновременно"


@pytest.mark.asyncio
async def test_create_borrow_record(mock_db):
    """Тестирует создание записи о выдаче книги."""
    mock_book = MagicMock(spec=Book, copies=1)
    borrow = BorrowCreate(book_id=1, reader_id=1)
    mock_borrow = MagicMock(spec=BorrowedBook, id=1)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.services.circulation.BorrowedBook", return_value=mock_borrow):
        with patch("app.services.circulation.BorrowRead.model_validate",
                   return_value=MagicMock(model_dump=lambda: {"id": 1})):
            result = await create_borrow_record(mock_db, borrow, mock_book)

    assert mock_book.copies == 0
    mock_db.add.assert_any_call(mock_borrow)
    mock_db.add.assert_any_call(mock_book)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_borrow)
    assert result.model_dump() == {"id": 1}


@pytest.mark.asyncio
async def test_check_borrow_record_success(mock_db):
    """Тестирует успешную проверку записи о выдаче."""
    mock_borrow = MagicMock(spec=BorrowedBook, book_id=1, reader_id=1)
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: mock_borrow)

    result = await check_borrow_record(mock_db, book_id=1, reader_id=1)
    assert result == mock_borrow
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_check_borrow_record_not_found(mock_db):
    """Тестирует случай, когда запись о выдаче не найдена."""
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: None)

    with pytest.raises(HTTPException) as exc:
        await check_borrow_record(mock_db, book_id=1, reader_id=1)
    assert exc.value.status_code == 404
    assert exc.value.detail == "Запись о выдаче не найдена или книга уже возвращена"


@pytest.mark.asyncio
async def test_return_borrowed_book(mock_db):
    """Тестирует возврат книги."""
    mock_book = MagicMock(spec=Book, copies=0)
    mock_borrow = MagicMock(spec=BorrowedBook, return_date=None)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.services.circulation.BorrowRead.model_validate",
               return_value=MagicMock(model_dump=lambda: {"id": 1})):
        result = await return_borrowed_book(mock_db, mock_borrow, mock_book)

    assert mock_book.copies == 1
    assert mock_borrow.return_date is not None
    mock_db.add.assert_any_call(mock_borrow)
    mock_db.add.assert_any_call(mock_book)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_borrow)
    assert result.model_dump() == {"id": 1}


@pytest.mark.asyncio
async def test_get_active_borrows(mock_db):
    """Тестирует получение списка активных выдач."""
    mock_borrow = MagicMock(spec=BorrowedBook, id=1)
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [mock_borrow]))

    with patch("app.services.circulation.BorrowRead.model_validate",
               return_value=MagicMock(model_dump=lambda: {"id": 1})):
        result = await get_active_borrows(mock_db, reader_id=1)

    assert len(result) == 1
    assert result[0].model_dump() == {"id": 1}
    mock_db.execute.assert_called_once()
from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.book import Book
from app.models.borrowed_book import BorrowedBook
from app.models.reader import Reader
from app.schemas.borrow import BorrowCreate, BorrowRead


async def check_book_exists(db: AsyncSession, book_id: int) -> Book:
    """Проверяет существование книги по ID."""
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book


async def check_reader_exists(db: AsyncSession, reader_id: int) -> Reader:
    """Проверяет существование читателя по ID."""
    result = await db.execute(select(Reader).where(Reader.id == reader_id))
    reader = result.scalar_one_or_none()
    if not reader:
        raise HTTPException(status_code=404, detail="Читатель не найден")
    return reader


async def check_book_availability(book: Book) -> None:
    """Проверяет наличие доступных экземпляров книги."""
    if book.copies < 1:
        raise HTTPException(status_code=400, detail="Нет доступных экземпляров книги")

async def check_borrow_limit(db: AsyncSession, reader_id: int) -> None:
    """Проверяет, не превышен ли лимит в 3 книги для читателя."""
    result = await db.execute(
        select(BorrowedBook).where(
            BorrowedBook.reader_id == reader_id,
            BorrowedBook.return_date.is_(None)
        )
    )
    active_borrows = len(result.scalars().all())
    if active_borrows >= 3:
        raise HTTPException(status_code=400, detail="Читатель не может взять более 3 книг одновременно")


async def create_borrow_record(db: AsyncSession, borrow: BorrowCreate, book: Book) -> BorrowRead:
    """Создаёт запись о выдаче книги и обновляет количество экземпляров."""
    new_borrow = BorrowedBook(
        book_id=borrow.book_id,
        reader_id=borrow.reader_id,
        borrow_date=datetime.now()
    )
    book.copies -= 1
    db.add(new_borrow)
    db.add(book)
    await db.commit()
    await db.refresh(new_borrow)
    return BorrowRead.model_validate(new_borrow)


async def check_borrow_record(db: AsyncSession, book_id: int, reader_id: int) -> BorrowedBook:
    """Проверяет существование записи о выдаче книги и её актуальность."""
    result = await db.execute(
        select(BorrowedBook).where(
            BorrowedBook.book_id == book_id,
            BorrowedBook.reader_id == reader_id,
            BorrowedBook.return_date.is_(None)
        )
    )
    borrow_record = result.scalar_one_or_none()
    if not borrow_record:
        raise HTTPException(status_code=404, detail="Запись о выдаче не найдена или книга уже возвращена")
    return borrow_record


async def return_borrowed_book(db: AsyncSession, borrow_record: BorrowedBook, book: Book) -> BorrowRead:
    """Обновляет запись о возврате книги и увеличивает количество экземпляров."""
    borrow_record.return_date = datetime.now()
    book.copies += 1
    db.add(borrow_record)
    db.add(book)
    await db.commit()
    await db.refresh(borrow_record)
    return BorrowRead.model_validate(borrow_record)


async def get_active_borrows(db: AsyncSession, reader_id: int) -> list[BorrowRead]:
    """Получает список активных выдач для читателя."""
    result = await db.execute(
        select(BorrowedBook).where(
            BorrowedBook.reader_id == reader_id,
            BorrowedBook.return_date.is_(None)
        )
    )
    borrows = result.scalars().all()
    return [BorrowRead.model_validate(borrow) for borrow in borrows]
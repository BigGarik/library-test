from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import JSONResponse

from app.models.book import Book
from app.models.borrowed_book import BorrowedBook
from app.models.reader import Reader
from app.schemas.borrow import BorrowCreate, BorrowRead
from app.utils.dependencies import get_db, get_current_user

router = APIRouter(prefix="/circulation", tags=["Выдача и возврат книг"])


@router.post("/borrow",
             response_model=BorrowRead,
             status_code=status.HTTP_201_CREATED,
             summary="Выдача книги"
             )
async def borrow_book(
        borrow: BorrowCreate,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Выдаёт книгу читателю.

    Требует аутентификации JWT. Проверяет наличие доступных экземпляров книги и лимит в 3 книги на читателя.
    Уменьшает количество экземпляров книги на 1 и создаёт запись в borrowed_books.
    Возвращает данные о выдаче и заголовок Location с адресом /borrow/{id}.

    Args:
        borrow: Данные о выдаче (book_id, reader_id).

    Raises:
        HTTPException(404): Если книга или читатель не найдены.
        HTTPException(400): Если нет доступных экземпляров или превышен лимит в 3 книги.
    """

    result = await db.execute(select(Book).where(Book.id == borrow.book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")


    result = await db.execute(select(Reader).where(Reader.id == borrow.reader_id))
    reader = result.scalar_one_or_none()
    if not reader:
        raise HTTPException(status_code=404, detail="Читатель не найден")


    if book.copies < 1:
        raise HTTPException(status_code=400, detail="Нет доступных экземпляров книги")

    result = await db.execute(
        select(BorrowedBook).where(
            BorrowedBook.reader_id == borrow.reader_id,
            BorrowedBook.return_date.is_(None)
        )
    )
    active_borrows = len(result.scalars().all())
    if active_borrows >= 3:
        raise HTTPException(status_code=400, detail="Читатель не может взять более 3 книг одновременно")

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
    return JSONResponse(
        content=BorrowRead.model_validate(new_borrow).model_dump(),
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/borrow/{new_borrow.id}"}
    )


@router.post("/return",
             response_model=BorrowRead,
             status_code=status.HTTP_200_OK,
             summary="Возврат книги")
async def return_book(
        borrow: BorrowCreate,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Возвращает книгу, взятую читателем.

    Требует аутентификации JWT. Проверяет, что книга была выдана указанному читателю и ещё не возвращена.
    Увеличивает количество экземпляров книги на 1 и устанавливает дату возврата в borrowed_books.
    Возвращает обновлённую запись о выдаче.

    Args:
        borrow: Данные о возврате (book_id, reader_id).

    Raises:
        HTTPException(404): Если книга, читатель или запись о выдаче не найдены.
        HTTPException(400): Если книга уже возвращена.
    """

    result = await db.execute(select(Book).where(Book.id == borrow.book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")

    result = await db.execute(select(Reader).where(Reader.id == borrow.reader_id))
    reader = result.scalar_one_or_none()
    if not reader:
        raise HTTPException(status_code=404, detail="Читатель не найден")

    result = await db.execute(
        select(BorrowedBook).where(
            BorrowedBook.book_id == borrow.book_id,
            BorrowedBook.reader_id == borrow.reader_id,
            BorrowedBook.return_date.is_(None)
        )
    )
    borrow_record = result.scalar_one_or_none()
    if not borrow_record:
        raise HTTPException(status_code=404, detail="Запись о выдаче не найдена или книга уже возвращена")

    borrow_record.return_date = datetime.now()
    book.copies += 1
    db.add(borrow_record)
    db.add(book)
    await db.commit()
    await db.refresh(borrow_record)
    return JSONResponse(
        content=BorrowRead.model_validate(borrow_record).model_dump(),
        status_code=status.HTTP_200_OK,
        headers={"Location": f"/borrow/{borrow_record.id}"}
    )

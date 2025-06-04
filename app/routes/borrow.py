from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.schemas.borrow import BorrowCreate, BorrowRead
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
from app.utils.dependencies import get_db, get_current_user

router = APIRouter(prefix="/circulation", tags=["Выдача и возврат книг"])


@router.post("/borrow",
             response_model=BorrowRead,
             status_code=status.HTTP_201_CREATED,
             summary="Выдача книги")
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
    book = await check_book_exists(db, borrow.book_id)
    await check_reader_exists(db, borrow.reader_id)
    await check_book_availability(book)
    await check_borrow_limit(db, borrow.reader_id)
    new_borrow = await create_borrow_record(db, borrow, book)
    return JSONResponse(
        content=new_borrow.model_dump(),
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
    book = await check_book_exists(db, borrow.book_id)
    await check_reader_exists(db, borrow.reader_id)
    borrow_record = await check_borrow_record(db, borrow.book_id, borrow.reader_id)
    updated_borrow = await return_borrowed_book(db, borrow_record, book)
    return JSONResponse(
        content=updated_borrow.model_dump(),
        status_code=status.HTTP_200_OK,
        headers={"Location": f"/borrow/{updated_borrow.id}"}
    )


@router.get("/{reader_id}",
            response_model=list[BorrowRead],
            status_code=status.HTTP_200_OK,
            summary="Список взятых книг читателем")
async def get_reader_borrows(
        reader_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Получает список всех книг, взятых читателем и ещё не возвращённых.

    Требует аутентификации JWT. Возвращает записи о выдаче, где return_date равен NULL.

    Args:
        reader_id: Идентификатор читателя.

    Raises:
        HTTPException(404): Если читатель не найден.
    """
    await check_reader_exists(db, reader_id)
    borrows = await get_active_borrows(db, reader_id)
    return JSONResponse(
        content=[borrow.model_dump() for borrow in borrows],
        status_code=status.HTTP_200_OK
    )

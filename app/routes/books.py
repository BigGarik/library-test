from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import JSONResponse

from app.models.book import Book
from app.schemas.book import BookCreate, BookUpdate, BookRead
from app.utils.dependencies import get_db, get_current_user

router = APIRouter(prefix="/books", tags=["Книги"])


@router.post("/", response_model=BookRead, status_code=status.HTTP_201_CREATED, summary="Добавить новую книгу")
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Создание новой книги.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    ## Описание:
    Этот эндпоинт позволяет создать новую книгу в библиотеке.
    Перед добавлением проверяется, существует ли уже книга с таким же ISBN.
    Если ISBN уже используется, возвращается ошибка `400 Bad Request`.

    ## Тело запроса:
    Модель `BookCreate`, включает следующие поля:

    - **title** (`str`, обязательно): Название книги.
      Пример: `"1984"`

    - **author** (`str`, обязательно): Автор книги.
      Пример: `"George Orwell"`

    - **year** (`int`, необязательно): Год издания.
      Пример: `1949`

    - **isbn** (`str`, обязательно): Международный стандартный книжный номер.
      Пример: `"978-0451524935"`

    - **copies** (`int`, по умолчанию `1`): Количество экземпляров книги.
      Должно быть неотрицательным (`>= 0`).

    - **description** (`str`, необязательно): Краткое описание книги.
      Пример: `"Антиутопический роман о тоталитарном государстве."`

    ## Ответ:
    - `201 Created`: Книга успешно создана.
      В теле ответа содержится сериализованный объект `BookRead`.
    - Заголовок `Location`: путь к созданной книге (`/books/{id}`).

    ## Ошибки:
    - `400 Bad Request`: Книга с указанным ISBN уже существует.
    - `401 Unauthorized`: Пользователь не аутентифицирован.
    """
    if book.isbn:
        result = await db.execute(select(Book).where(Book.isbn == book.isbn))
        existing = result.scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=400,
                detail="ISBN уже существует"
            )

    new_book = Book(**book.model_dump())
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    return JSONResponse(
        content=BookRead.model_validate(new_book).model_dump(),
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/books/{new_book.id}"}
    )


@router.get("/", response_model=list[BookRead], summary="Получить список всех книг")
async def get_books(
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Получение списка всех книг.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    ## Описание:
    Этот эндпоинт позволяет получить список всех книг, доступных в библиотеке.
    Возвращает массив объектов `BookRead`.

    ## Ответ:
    - `200 OK`: Список книг успешно получен.
    - `401 Unauthorized`: Пользователь не аутентифицирован.
    """
    result = await db.execute(select(Book))
    return result.scalars().all()


@router.get("/{book_id}",
            response_model=BookRead,
            summary="Получить книгу по ID"
            )
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Получение информации о конкретной книге по ID.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    ## Описание:
    Этот эндпоинт возвращает подробную информацию о книге с заданным `book_id`.

    ## Параметры:
    - **book_id** (`int`, обязательно): Уникальный идентификатор книги.

    ## Ответ:
    - `200 OK`: Книга найдена и возвращена.
    - `404 Not Found`: Книга с указанным ID не найдена.
    - `401 Unauthorized`: Пользователь не аутентифицирован.
    """
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(status_code=404, detail="Книга не найдена")
    return book


@router.put("/{book_id}",
            response_model=BookRead,
            summary="Обновить книгу по ID")
async def update_book(
    book_id: int,
    book_data: BookUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Обновление информации о книге.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    ## Описание:
    Этот эндпоинт позволяет обновить информацию о существующей книге.
    Передаются только изменяемые поля. Поля, отсутствующие в запросе, остаются без изменений.

    ## Параметры:
    - **book_id** (`int`, обязательно): Уникальный идентификатор книги.

    ## Тело запроса:
    Модель `BookUpdate`, включает следующие поля (все необязательны):

    - **title** (`str`): Название книги.
    - **author** (`str`): Автор книги.
    - **year** (`int`): Год издания.
    - **isbn** (`str`): Международный стандартный книжный номер.
    - **copies** (`int`): Количество экземпляров книги.
    - **description** (`str`): Краткое описание книги.

    ## Ответ:
    - `200 OK`: Книга успешно обновлена.
    - `404 Not Found`: Книга с указанным ID не найдена.
    - `401 Unauthorized`: Пользователь не аутентифицирован.
    """
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()

    if not book:
        raise HTTPException(
            status_code=404,
            detail="Книга не найдена"
        )

    for field, value in book_data.model_dump(exclude_unset=True).items():
        setattr(book, field, value)

    db.add(book)
    await db.commit()
    await db.refresh(book)
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Удалить книгу по ID")
async def delete_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    user=Depends(get_current_user)
):
    """
    Удаление книги по ID.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    ## Описание:
    Этот эндпоинт позволяет удалить книгу из библиотеки по заданному `book_id`.

    ## Параметры:
    - **book_id** (`int`, обязательно): Уникальный идентификатор книги.

    ## Ответ:
    - `204 No Content`: Книга успешно удалена.
    - `404 Not Found`: Книга с указанным ID не найдена.
    - `401 Unauthorized`: Пользователь не аутентифицирован.
    """
    result = await db.execute(select(Book).where(Book.id == book_id))
    book = result.scalar_one_or_none()
    if not book:
        raise HTTPException(
            status_code=404,
            detail="Книга не найдена")

    await db.delete(book)
    await db.commit()

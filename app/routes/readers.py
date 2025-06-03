from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from starlette.responses import JSONResponse

from app.models.reader import Reader
from app.schemas.reader import ReaderCreate, ReaderRead, ReaderUpdate
from app.utils.dependencies import get_db, get_current_user

router = APIRouter(prefix="/readers", tags=["Читатели"])


@router.post("/",
             response_model=ReaderRead,
             status_code=status.HTTP_201_CREATED,
             summary="Добавить нового читателя")
async def create_reader(
        reader: ReaderCreate,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Создаёт нового читателя в библиотечной системе.

    ## Требования:
        - Пользователь должен быть аутентифицирован.

    Проверяет уникальность email.
    Возвращает созданного читателя с его ID и заголовок Location с адресом /readers/{id}.

    Args:
        reader: Данные читателя, содержащие имя и email.

    Raises:
        HTTPException(400): Если читатель с указанным email уже существует.
    """
    result = await db.execute(select(Reader).where(Reader.email == reader.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Читатель с таким Email уже существует")
    new_reader = Reader(**reader.model_dump())
    db.add(new_reader)
    await db.commit()
    await db.refresh(new_reader)
    return JSONResponse(
        content=ReaderRead.model_validate(new_reader).model_dump(),
        status_code=status.HTTP_201_CREATED,
        headers={"Location": f"/readers/{new_reader.id}"}
    )


@router.get("/",
            response_model=list[ReaderRead],
            summary="Получить всех читателей"
            )
async def get_readers(
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Получает список всех читателей в библиотечной системе.

    Требует аутентификации JWT.
    Возвращает всех читателей из базы данных.
    """
    result = await db.execute(select(Reader))
    return result.scalars().all()


@router.get("/{reader_id}",
            response_model=ReaderRead,
            summary="Получить читателя по ID"
            )
async def get_reader(
        reader_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Получает читателя по его ID.

    Требует аутентификации JWT.

    Args:
        reader_id: ID читателя для получения.

    Raises:
        HTTPException(404): Если читатель не найден.
    """
    result = await db.execute(select(Reader).where(Reader.id == reader_id))
    reader = result.scalar_one_or_none()
    if not reader:
        raise HTTPException(
            status_code=404,
            detail="Читатель не найден"
        )
    return reader


@router.put("/{reader_id}",
            response_model=ReaderRead,
            summary="Обновить читателя по ID"
            )
async def update_reader(
        reader_id: int,
        reader_data: ReaderUpdate,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Обновляет данные существующего читателя по его ID.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    Поддерживает частичное обновление (изменяются только переданные поля).
    Проверяет уникальность email, если он указан.

    Args:
        reader_id: ID читателя для обновления.
        reader_data: Поля для обновления.

    Raises:
        HTTPException(404): Если читатель не найден.
        HTTPException(400): Если новый email уже существует.
    """
    result = await db.execute(select(Reader).where(Reader.id == reader_id))
    reader = result.scalar_one_or_none()

    if not reader:
        raise HTTPException(
            status_code=404,
            detail="Читатель не найден"
        )

    if reader_data.email and reader_data.email != reader.email:
        result = await db.execute(select(Reader).where(Reader.email == reader_data.email))
        if result.scalar_one_or_none():

            raise HTTPException(
                status_code=400,
                detail="Читатель с таким email уже существует"
            )

    for key, value in reader_data.model_dump(exclude_unset=True).items():
        setattr(reader, key, value)

    await db.commit()
    await db.refresh(reader)
    return reader


@router.delete("/{reader_id}",
               status_code=status.HTTP_204_NO_CONTENT,
               summary="Удалить читателя по ID"
               )
async def delete_reader(
        reader_id: int,
        db: AsyncSession = Depends(get_db),
        user=Depends(get_current_user)
):
    """Удаляет читателя по его ID.

    ## Требования:
    - Пользователь должен быть аутентифицирован.

    Args:
        reader_id: ID читателя для удаления.

    Raises:
        HTTPException(404): Если читатель не найден.
    """
    result = await db.execute(select(Reader).where(Reader.id == reader_id))
    reader = result.scalar_one_or_none()

    if not reader:
        raise HTTPException(
            status_code=404,
            detail="Читатель не найден"
        )

    await db.delete(reader)
    await db.commit()
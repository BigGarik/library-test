from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, Token
from app.utils.auth import hash_password, verify_password, create_access_token
from app.utils.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/register", response_model=Token, summary="Регистрация нового пользователя")
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Регистрация нового пользователя в системе.

    ## Описание:
    Создает новую учетную запись пользователя с указанным email и паролем.
    После успешной регистрации автоматически выдается токен доступа.

    ## Тело запроса:
    Модель `UserCreate` со следующими полями:
    - **email** (`str`, обязательно): Электронная почта пользователя (должна быть уникальной)
    - **password** (`str`, обязательно): Пароль пользователя (минимум 8 символов)

    ## Ответы:
    - `200 OK`: Пользователь успешно зарегистрирован, возвращается токен доступа
    - `400 Bad Request`: Пользователь с таким email уже существует
    - `422 Unprocessable Entity`: Некорректные данные в запросе

    ## Возвращает:
    Объект `Token` с полем `access_token` для доступа к защищенным эндпоинтам.
    """

    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже существует"
        )

    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(data={"sub": str(new_user.id)})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token, summary="Авторизация пользователя")
async def login_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
):
    """
    Авторизация пользователя в системе.

    ## Описание:
    Проверяет учетные данные пользователя (email и пароль) и выдает токен доступа
    при успешной аутентификации.

    ## Параметры формы:
    - **username** (`str`, обязательно): Email пользователя
    - **password** (`str`, обязательно): Пароль пользователя

    ## Ответы:
    - `200 OK`: Успешная авторизация, возвращается токен доступа
    - `401 Unauthorized`: Неверные учетные данные (неправильный email или пароль)
    - `422 Unprocessable Entity`: Некорректные данные в запросе

    ## Возвращает:
    Объект `Token` с полем `access_token` для доступа к защищенным эндпоинтам.

    ## Примечание:
    Токен имеет ограниченное время жизни и должен использоваться в заголовке
    `Authorization: Bearer <token>` для доступа к защищенным ресурсам.
    """

    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверные учетные данные"
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)

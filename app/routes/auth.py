from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, Token
from app.utils.auth import hash_password, verify_password, create_access_token
from app.utils.dependencies import get_db

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    # Проверка существования пользователя
    result = await db.execute(select(User).where(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")

    # Создание пользователя
    new_user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Генерация JWT
    access_token = create_access_token(data={"sub": str(new_user.id)})
    return Token(access_token=access_token)


@router.post("/login", response_model=Token)
async def login_user(user_data: UserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == user_data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)

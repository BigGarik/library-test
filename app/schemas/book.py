from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class BookBase(BaseModel):
    """Базовая модель книги с общими полями"""
    title: str = Field(..., description="Название книги", json_schema_extra={"example": "1984"})
    author: str = Field(..., description="Автор книги", json_schema_extra={"example": "George Orwell"})
    year: Optional[int] = Field(None, description="Год издания", json_schema_extra={"example": 1949})
    isbn: str = Field(..., description="Международный стандартный книжный номер", json_schema_extra={"example": "978-0451524935"})
    copies: int = Field(1, ge=0, description="Количество экземпляров", json_schema_extra={"example": 3})
    description: Optional[str] = Field(None, description="Краткое описание книги", json_schema_extra={"example": "Антиутопический роман о тоталитарном государстве."})


class BookCreate(BookBase):
    """Модель для создания книги"""
    pass


class BookUpdate(BaseModel):
    """Модель для обновления книги - все поля опциональны"""
    title: Optional[str] = Field(None, description="Название книги", json_schema_extra={"example": "1984"})
    author: Optional[str] = Field(None, description="Автор книги", json_schema_extra={"example": "George Orwell"})
    year: Optional[int] = Field(None, description="Год издания", json_schema_extra={"example": 1949})
    isbn: Optional[str] = Field(None, description="Международный стандартный книжный номер", json_schema_extra={"example": "978-0451524935"})
    copies: Optional[int] = Field(None, ge=0, description="Количество экземпляров книги (не может быть отрицательным)", json_schema_extra={"example": 3})
    description: Optional[str] = Field(None, description="Краткое описание книги", json_schema_extra={"example": "Антиутопический роман о тоталитарном государстве."})


class BookRead(BookBase):
    """Модель для чтения книги с ID"""
    id: int
    model_config = ConfigDict(from_attributes=True)
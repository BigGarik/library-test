from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional


class ReaderBase(BaseModel):
    name: str = Field(..., description="Имя читателя", json_schema_extra={"example": "Иван Иванов"})
    email: EmailStr = Field(..., description="Email читателя", json_schema_extra={"example": "ivan@example.com"})


class ReaderCreate(ReaderBase):
    pass


class ReaderUpdate(BaseModel):
    name: Optional[str] = Field(None, description="Имя читателя", json_schema_extra={"example": "Иван Иванов"})
    email: Optional[EmailStr] = Field(None, description="Email читателя", json_schema_extra={"example": "ivan@example.com"})


class ReaderRead(ReaderBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
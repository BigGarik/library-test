from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class BorrowCreate(BaseModel):
    book_id: int = Field(..., description="Идентификатор книги, которую берёт читатель", json_schema_extra={"example": 1})
    reader_id: int = Field(..., description="Идентификатор читателя, берущего книгу", json_schema_extra={"example": 1})

class BorrowRead(BaseModel):
    id: int = Field(..., description="Идентификатор записи о выдаче")
    book_id: int = Field(..., description="Идентификатор выданной книги", json_schema_extra={"example": 1})
    reader_id: int = Field(..., description="Идентификатор читателя, взявшего книгу", json_schema_extra={"example": 1})
    borrow_date: datetime = Field(..., description="Дата выдачи книги")
    return_date: Optional[datetime] = Field(None, description="Дата возврата книги, если она возвращена")

    model_config = ConfigDict(from_attributes=True)
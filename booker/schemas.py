from datetime import datetime
from typing import Optional

from pydantic_core.core_schema import ValidationInfo
from pydantic import BaseModel, ConfigDict, field_validator


class RoomCreate(BaseModel):
    name: str
    location: Optional[str] = None


class RoomRead(RoomCreate):
    id: int

    # Allow model creation from object attributes so that Pydantic can properly deal with
    # ORM models like those returned from sqlalchemy.
    model_config = ConfigDict(from_attributes=True)


class BookingCreate(BaseModel):
    room_id: int
    user_name: str
    start_datetime: datetime
    end_datetime: datetime

    @field_validator("end_datetime")
    def end_must_be_after_start(cls, end, info: ValidationInfo):
        if "start_datetime" in info.data and end <= info.data["start_datetime"]:
            raise ValueError("end_datetime must be after start_datetime")
        return end


class BookingRead(BookingCreate):
    id: int

    model_config = ConfigDict(from_attributes=True)

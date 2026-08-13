from enum import Enum

from beanie import DocumentWithSoftDelete
from pydantic import BaseModel, EmailStr


class PhoneNumber(BaseModel):
    number: int
    country_code: int
    country: str
    prefix: str


class Role(str,Enum):
    ADMIN = "admin"
    USER = "user"
    SUPER_ADMIN = "super_admin"
    GUEST = "guest"


class User(DocumentWithSoftDelete):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    hashed_password: str
    phone_number: PhoneNumber | None = None
    role:Role = Role.USER

    class Settings:
        name = "user"

from pydantic import BaseModel, EmailStr

from app.models.auth import Token
from app.models.user import PhoneNumber


class LoginData(BaseModel):
    email: EmailStr
    password: str
    remember_me: bool = False


class LoginResponse(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    phone_number: PhoneNumber | None
    token: Token

class RegisterData(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    phone_number: PhoneNumber | None = None
    password:str

class RegisterResponse(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    phone_number: PhoneNumber | None = None
    token: Token

from pydantic import BaseModel, EmailStr, Field

from app.models.user import PhoneNumber, Role, User


class UserResponse(User):
    hashed_password: str = Field(exclude=True)

class UserUpdateData(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone_number: PhoneNumber | None = None
    role: Role | None = None

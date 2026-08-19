from typing import Any, cast

from beanie import PydanticObjectId
from beanie.operators import Or, RegEx

from app.core.error import ConflictError, NotFoundError
from app.models.user import User
from app.schemas.common import ListResponsePaginated, PaginationMeta
from app.schemas.user import UserUpdateData


class UserService:
    def __init__(self) -> None:
        self.userRepo = User

    async def findById(self, user_id: str):
        user = await self.userRepo.find_one(
            self.userRepo.id == PydanticObjectId(user_id)
        )
        if not user:
            raise NotFoundError("User not found")
        return user

    async def findAll(self, page: int = 1, limit: int = 10, s: str | None = None):
        skip = (page - 1) * limit
        query = self.userRepo.find()
        if s:
            conditions: list[Any] = [
                RegEx(self.userRepo.first_name, s, "i"),
                RegEx(self.userRepo.last_name, s, "i"),
                RegEx(self.userRepo.email, s, "i"),
            ]
            if s.isdigit():
                phone_field = cast(Any, self.userRepo.phone_number).number
                conditions.append(phone_field == int(s))
            query = query.find(Or(*conditions))
        total_items = await query.count()
        total_pages = (total_items + limit - 1) // limit
        users = await query.skip(skip).limit(limit).to_list()
        pagination_meta = PaginationMeta(
            page=page,
            per_page=limit,
            total_pages=total_pages,
            total_items=total_items,
        )
        return ListResponsePaginated[User](data=users, pagination_meta=pagination_meta)

    async def updateById(self, user_id: str, data: UserUpdateData):
        user = await self.userRepo.find_one(
            self.userRepo.id == PydanticObjectId(user_id)
        )
        if not user:
            raise NotFoundError("User not found")

        update_fields = data.model_dump(exclude_unset=True, exclude_none=True)
        if not update_fields:
            return user

        if "email" in update_fields and update_fields["email"] != user.email:
            existing = await self.userRepo.find_one(
                self.userRepo.email == update_fields["email"]
            )
            if existing:
                raise ConflictError("Email already registered")

        await user.set(update_fields)
        return user

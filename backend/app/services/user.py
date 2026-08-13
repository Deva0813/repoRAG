from beanie import PydanticObjectId

from app.core.error import NotFoundError
from app.models.user import User


class UserService:
    @staticmethod
    async def findById(user_id: str) -> User:
        user = await User.find_one(User.id == PydanticObjectId(user_id))
        if (not user) or (user.is_deleted()):
            raise NotFoundError("User not found")
        return user

    @staticmethod
    async def findAll(page: int = 1, limit: int = 10) -> list[User]:
        skip = (page - 1) * limit
        users = await User.find_all(skip, limit).to_list()
        return users

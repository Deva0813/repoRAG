from app.schemas.user import UserUpdateData
from app.services.user import UserService


class UserController:
    def __init__(self) -> None:
        self._userService = UserService()

    async def findById(self, user_id: str):
        user = await self._userService.findById(user_id)
        return user

    async def findAll(self,page:int=1,limit:int=10,s:str|None=None):
        users = await self._userService.findAll(page,limit,s)
        return users

    async def updateById(self, user_id: str, data: UserUpdateData):
        user = await self._userService.updateById(user_id,data)
        return user

controller = UserController()

__all__ = ["controller"]

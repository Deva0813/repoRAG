from beanie import init_beanie
from pymongo import AsyncMongoClient

from app.core.config import settings
from app.models.auth import RefreshToken
from app.models.user import User


async def init_db():
    client = AsyncMongoClient(settings.mongo_uri,tz_aware=True)
    await init_beanie(database=client[settings.db_name], document_models=[User,RefreshToken])

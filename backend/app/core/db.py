from beanie import init_beanie
from pymongo import AsyncMongoClient
from pymongo.operations import SearchIndexModel

from app.core.config import settings
from app.models.auth import RefreshToken
from app.models.rag import CodeChunk, Repository
from app.models.user import User


async def init_db():
    client = AsyncMongoClient(settings.mongo_uri, tz_aware=True)
    await init_beanie(
        database=client[settings.db_name],
        document_models=[User, RefreshToken, Repository, CodeChunk],
    )
    await create_vector_search_index()


async def create_vector_search_index():
    collection = CodeChunk.get_pymongo_collection()
    db = collection.database
    existing = await db.list_collection_names()
    if collection.name not in existing:
        await db.create_collection(collection.name)
    index = SearchIndexModel(
        definition={
            "fields": [
                {
                    "numDimensions": 1024,
                    "path": "embedding",
                    "similarity": "cosine",
                    "type": "vector",
                },
                {"path": "repository_id", "type": "filter"},
            ]
        },
        name="code_chunks_vector_index",
        type="vectorSearch",
    )
    await collection.create_search_index(model=index)

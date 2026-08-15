from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.db import init_db
from app.core.error import register_error_handlers
from app.core.logger import setup_logging
from app.routes import auth, user

setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield


app = FastAPI(title="RepoRAG", lifespan=lifespan)
register_error_handlers(app)
app.add_middleware(CORSMiddleware)

app.include_router(auth.router)
app.include_router(user.router)

@app.get("/")
async def home():
    return {"repoRAG": "Hey man!!!"}

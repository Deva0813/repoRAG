from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.celery_app import celery_app
from app.core.db import init_db
from app.core.error import register_error_handlers
from app.core.logger import setup_logging
from app.routes import auth, user
from app.tasks.tasks import long_running_task

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
    task = celery_app.send_task("long_running_task", args=[5, 6])
    return {"repoRAG": "Hey man!!!"}

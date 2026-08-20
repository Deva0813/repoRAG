import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from beanie import PydanticObjectId
from langchain_core.documents import Document

from app.core.config import settings
from app.core.error import ApiError, ConflictError, NotFoundError
from app.core.llm import embeddings, llm
from app.models.rag import CodeChunk, Repository, RepoStatus
from app.schemas.rag import ChatRequest, RepositoryMeta
from app.utils.rag_config import (
    RAG_PROMPT,
    get_language,
    is_supported_file,
    safe_read_file,
)


class RAGService:
    def __init__(self) -> None:
        self.repositoryRepo = Repository
        self.codeChunkRepo = CodeChunk

    def clone_repository(
        self,
        github_url: str,
        destination: str,
    ) -> None:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                github_url,
                destination,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    def discover_files(self, repository_path: str) -> list[Path]:
        root = Path(repository_path)
        files = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if not is_supported_file(path):
                continue
            files.append(path)
        return files

    def chunk_file(
        self,
        content: str,
        file_path: str,
        language: str,
    ) -> list[Document]:

        lines = content.splitlines()

        documents: list[Document] = []

        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        start = 0

        while start < len(lines):
            end = min(
                start + chunk_size,
                len(lines),
            )
            chunk_lines = lines[start:end]
            chunk_content = "\n".join(chunk_lines)
            if chunk_content.strip():
                documents.append(
                    Document(
                        page_content=chunk_content,
                        metadata={
                            "file_path": file_path,
                            "language": language,
                            "start_line": start + 1,
                            "end_line": end,
                        },
                    )
                )
            if end >= len(lines):
                break
            start = max(
                end - overlap,
                start + 1,
            )
        return documents

    def load_repository_documents(
        self,
        repository_path: str,
    ) -> list[Document]:
        documents: list[Document] = []
        files = self.discover_files(repository_path)
        root = Path(repository_path)
        for file in files:
            content = safe_read_file(file)
            if not content:
                continue
            relative_path = str(file.relative_to(root)).replace("\\", "/")
            language = get_language(file.suffix)
            file_documents = self.chunk_file(
                content=content,
                file_path=relative_path,
                language=language,
            )
            documents.extend(file_documents)
        return documents

    def generate_embeddings(
        self,
        documents: list[Document],
    ) -> list[list[float]]:
        texts = [document.page_content for document in documents]
        return embeddings.embed_documents(texts)

    async def insert_chunks(
        self,
        repository_id: str,
        documents: list[Document],
        vectors: list[list[float]],
    ):
        if not documents:
            return
        records = []
        for document, vector in zip(
            documents,
            vectors,
        ):
            metadata = document.metadata
            records.append(
                self.codeChunkRepo(
                    repository_id=repository_id,
                    content=document.page_content,
                    embedding=vector,
                    file_path=metadata["file_path"],
                    language=metadata["language"],
                    start_line=metadata["start_line"],
                    end_line=metadata["end_line"],
                )
            )
        # Insert in batches.
        batch_size = 100
        for i in range(
            0,
            len(records),
            batch_size,
        ):
            batch = records[i : i + batch_size]
            await self.codeChunkRepo.insert_many(batch)

    async def run_indexing(
        self,
        repository_id: str,
        github_url: str,
    ):
        temporary_directory = tempfile.mkdtemp(prefix="reporag_")
        try:
            await self.repositoryRepo.find_one(
                self.repositoryRepo.id == PydanticObjectId(repository_id)
            ).set({self.repositoryRepo.status: RepoStatus.CLONING})
            self.clone_repository(
                github_url,
                temporary_directory,
            )
            print(temporary_directory)
            await self.repositoryRepo.find_one(
                self.repositoryRepo.id == PydanticObjectId(repository_id)
            ).set({self.repositoryRepo.status: RepoStatus.SCANNING})
            documents = self.load_repository_documents(temporary_directory)
            await self.repositoryRepo.find_one(
                self.repositoryRepo.id == PydanticObjectId(repository_id)
            ).set(
                {
                    self.repositoryRepo.status: RepoStatus.EMBEDDING,
                    self.repositoryRepo.total_chunks: len(documents),
                }
            )
            vectors = self.generate_embeddings(documents)
            await self.insert_chunks(
                repository_id=repository_id,
                documents=documents,
                vectors=vectors,
            )
            await self.repositoryRepo.find_one(
                self.repositoryRepo.id == PydanticObjectId(repository_id)
            ).set(
                {
                    self.repositoryRepo.status: RepoStatus.COMPLETED,
                    self.repositoryRepo.total_chunks: len(documents),
                }
            )
            return {
                "status": "completed",
                "chunks": len(documents),
            }
        except Exception as exc:
            await self.repositoryRepo.find_one(
                self.repositoryRepo.id == PydanticObjectId(repository_id)
            ).set(
                {
                    self.repositoryRepo.status: RepoStatus.FAILED,
                    self.repositoryRepo.error: str(exc),
                }
            )
            raise
        finally:
            shutil.rmtree(
                temporary_directory,
                ignore_errors=True,
            )

    async def vector_search(
        self,
        repository_id: str,
        query: str,
        top_k: int = 6,
    ) -> list[dict[str, Any]]:

        query_vector = embeddings.embed_query(query)
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "code_chunks_vector_index",
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": max(
                        top_k * 10,
                        50,
                    ),
                    "limit": top_k,
                    "filter": {"repository_id": repository_id},
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "content": 1,
                    "file_path": 1,
                    "language": 1,
                    "start_line": 1,
                    "end_line": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        # cursor = self.codeChunkRepo.aggregate(pipeline)

        # return await cursor.to_list(length=top_k)

        collection = self.codeChunkRepo.get_pymongo_collection()
        cursor = await collection.aggregate(pipeline)
        return await cursor.to_list(length=top_k)

    def build_context(
        self,
        documents: list[dict[str, Any]],
    ) -> tuple[str, list[dict[str, Any]]]:

        context_parts = []

        sources = []

        for index, document in enumerate(
            documents,
            start=1,
        ):
            source_id = index

            file_path = document["file_path"]

            start_line = document["start_line"]

            end_line = document["end_line"]

            content = document["content"]

            context_parts.append(
                f"""
                [{source_id}] {file_path}:{start_line}-{end_line}

                ```{document.get("language", "")}
                {content}
                ```
                """
            )
            sources.append(
                {
                    "id": source_id,
                    "file_path": file_path,
                    "start_line": start_line,
                    "end_line": end_line,
                    "score": document.get("score"),
                }
            )

        return "\n".join(context_parts), sources

    async def generate_answer(
        self,
        question: str,
        context: str,
    ) -> str | list[str | dict[Any, Any]]:
        chain = RAG_PROMPT | llm
        response = await chain.ainvoke(
            {
                "question": question,
                "context": context,
            }
        )
        return response.content

    async def create(self, data: Repository):
        res = await self.repositoryRepo.insert_one(data)
        if not res:
            raise ApiError("Unable to create repository")
        return res

    async def find_by_id(self, id: str):
        res = await self.repositoryRepo.find_one(
            self.repositoryRepo.id == PydanticObjectId(id)
        )
        if not res:
            raise NotFoundError("Repository not found")
        return res

    async def find_by_id_meta(self, id: str):
        res = await self.repositoryRepo.find_one(
            self.repositoryRepo.id == PydanticObjectId(id)
        ).project(RepositoryMeta)
        if not res:
            raise NotFoundError("Repository not found")
        return res

    async def update_celery_task_id(
        self,
        id: PydanticObjectId,
        celery_task_id: str,
        status: RepoStatus | None = None,
    ):
        res = await self.repositoryRepo.find_one(self.repositoryRepo.id == id)
        if not res:
            raise ApiError("Unable to update repository")
        if status:
            await res.set(
                {
                    self.repositoryRepo.celery_task_id: celery_task_id,
                    self.repositoryRepo.status: status,
                }
            )
        else:
            await res.set({self.repositoryRepo.celery_task_id: celery_task_id})
        return res

    async def chat(self, chat_data: ChatRequest):
        repo = await self.repositoryRepo.find_one(
            self.repositoryRepo.id == PydanticObjectId(chat_data.repository_id)
        )
        if not repo:
            raise NotFoundError("Repository not found")
        if repo.status != RepoStatus.COMPLETED:
            raise ConflictError("Repository is not indexed yet")

        docs = await self.vector_search(
            repository_id=chat_data.repository_id,
            query=chat_data.question,
            top_k=chat_data.top_k,
        )
        if not docs:
            return {
                "answer": ("I couldn't find relevant information in the repository."),
                "sources": [],
            }
        context, sources = self.build_context(docs)
        answer = await self.generate_answer(
            question=chat_data.question,
            context=context,
        )
        return {
            "answer": answer,
            "sources": sources,
        }

from langchain_ollama import ChatOllama, OllamaEmbeddings

from app.core.config import settings

embeddings = OllamaEmbeddings(
    model=settings.ollama_embedding_model,
    base_url=settings.ollama_base_url,
)

llm = ChatOllama(
    model=settings.ollama_chat_model,
    base_url=settings.ollama_base_url,
    temperature=0,
)

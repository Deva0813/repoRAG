from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cpp",
    ".c",
    ".cs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".kts",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
}

IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
}

RAG_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are RepoLens, an AI assistant specialized
in understanding software repositories.
Answer the user's question using ONLY the
provided repository context.
Rules:
1. Never invent files, functions, classes,
   APIs, dependencies, or behavior.
2. If the provided context is insufficient,
   clearly say that you don't have enough
   information.
3. Explain the answer clearly for a software
   engineer.
4. Cite relevant sources using [1], [2], etc.
5. Distinguish repository facts from
   reasonable inferences.
6. Prefer precise file and line references.
Repository context:
{context}
""",
        ),
        (
            "human",
            "{question}",
        ),
    ]
)


def get_language(extension: str) -> str:
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".cpp": "cpp",
        ".c": "c",
        ".cs": "csharp",
        ".rb": "ruby",
        ".php": "php",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".md": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
    }

    return mapping.get(extension.lower(), "text")


def safe_read_file(path: Path) -> str | None:
    if path.stat().st_size > 1_000_000:
        return None

    return path.read_text(
        encoding="utf-8",
        errors="ignore",
    )


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS and not any(
        directory in path.parts for directory in IGNORED_DIRECTORIES
    )

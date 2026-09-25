"""
Configuration settings for the AUTOSAR HLD Document Analysis Assistant.
Loads environment variables and sets up project paths.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(ROOT_DIR / ".env")

# Server Config
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_URL = os.getenv("BACKEND_URL", f"http://{BACKEND_HOST}:{BACKEND_PORT}")

# LLM Config
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20240620")
LOCAL_LLM_URL = os.getenv("LOCAL_LLM_URL", "http://localhost:11434/v1")
LOCAL_LLM_MODEL = os.getenv("LOCAL_LLM_MODEL", "llama3:8b")

# Embedding Config
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# Directories
DATA_DIR = ROOT_DIR / os.getenv("DATA_DIR", "app/data")
CHROMA_PERSIST_DIR = ROOT_DIR / os.getenv("CHROMA_PERSIST_DIR", "app/data/chroma_db")
SQLITE_DB_PATH = ROOT_DIR / os.getenv("SQLITE_DB_PATH", "app/data/autosar_analysis.db")
UPLOAD_DIR = ROOT_DIR / os.getenv("UPLOAD_DIR", "app/data/uploads")
SAMPLE_DOCS_DIR = ROOT_DIR / "app/sample_docs"

# Optional Tesseract OCR binary path
TESSERACT_CMD = os.getenv("TESSERACT_CMD", "")

# Ensure data directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

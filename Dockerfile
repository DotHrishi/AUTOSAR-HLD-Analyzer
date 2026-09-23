# Multi-stage Dockerfile for AUTOSAR HLD Document Analysis Assistant
FROM python:3.11-slim

# Install system dependencies including Tesseract OCR and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependency specifications
COPY requirements.txt .

# Install python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Generate sample documents on build
RUN python app/sample_docs/generate_sample_hld.py

# Expose FastAPI backend (8000) and Streamlit frontend (8501)
EXPOSE 8000 8501

# Default command starts FastAPI backend and Streamlit frontend
CMD ["sh", "-c", "uvicorn app.backend.main:app --host 0.0.0.0 --port 8000 & streamlit run app/frontend/app.py --server.port 8501 --server.address 0.0.0.0"]

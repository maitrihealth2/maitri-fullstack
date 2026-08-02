FROM python:3.12-slim

# Copy uv from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# System deps some ML libs need
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU first to avoid 5GB bloat using uv
RUN uv pip install --system --no-cache torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
# Use uv for extremely fast package resolution and installation
RUN uv pip install --system --no-cache -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Pre-download NLTK data required by rouge-score / tokenizers
RUN python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"

COPY . .

# Use the unified Python runner
CMD ["python", "main.py"]

FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# System dependencies required by runtime audio and ML packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN python -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
ENV PORT=8000
ENV RAG_AUTO_BUILD=true
CMD ["python", "main.py"]

# Use official lightweight Python image
FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=5000
ENV NO_BROWSER=true

# Install system dependencies including FFmpeg, NodeJS, and curl
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    nodejs \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Deno for yt-dlp YouTube JS cipher/challenge solving on cloud IPs
ENV DENO_INSTALL="/root/.deno"
ENV PATH="${DENO_INSTALL}/bin:${PATH}"
RUN curl -fsSL https://deno.land/install.sh | sh

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Ensure downloads directory exists with correct permissions
RUN mkdir -p downloads && chmod 777 downloads

# Expose server port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:5000/healthz || exit 1

# Start production server with Gunicorn (multithreaded for concurrent downloads)
CMD exec gunicorn app:app --workers 2 --threads 4 --timeout 360 --bind 0.0.0.0:${PORT}

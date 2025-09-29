FROM python:3.11-slim

# Set environment variables for pip optimization
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_DEFAULT_TIMEOUT=1000

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements-cpu.txt .

# Update pip and configure timeout settings
RUN pip install --upgrade pip

# Install PyTorch CPU version first (much smaller than CUDA version)
# This significantly reduces build time and image size
RUN pip install --timeout=1000 --retries=5 --no-cache-dir \
    torch==2.8.0+cpu \
    --index-url https://download.pytorch.org/whl/cpu

# Install remaining dependencies with increased timeout and retries
RUN pip install --timeout=1000 --retries=5 --no-cache-dir -r requirements-cpu.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM python:3.11-slim

# Prevent Python from writing pyc files and keep stdout unbuffered for immediate logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install OS-level dependencies required for lightweight text processing or networking
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    jq \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the harness codebase
COPY . .

# Set the default execution target to your evaluation script
ENTRYPOINT ["python", "evaluate.py"]
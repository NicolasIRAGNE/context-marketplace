FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
COPY mcp_requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r mcp_requirements.txt

# Copy application
COPY . .

# Create non-root user and set up directories
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/contexts && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "-m", "app.main"]
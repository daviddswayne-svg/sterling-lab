FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install system dependencies (removed nginx)
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  dos2unix \
  procps \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Make start script executable and fix line endings
RUN dos2unix start.sh && chmod +x start.sh

# Expose Streamlit and Flask API ports (internal to Docker network)
EXPOSE 8501 5000

# Health check (check Streamlit)
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Run the start script
CMD ["./start.sh"]


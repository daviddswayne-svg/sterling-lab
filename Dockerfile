FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  nginx \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Move nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Make start script executable
RUN chmod +x start.sh

# Expose HTTP port
EXPOSE 80

# Health check (check Nginx)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

# Run the start script
CMD ["./start.sh"]

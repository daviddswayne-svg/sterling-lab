FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
  build-essential \
  curl \
  nginx \
  dos2unix \
  procps \
  && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Move nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Make start script executable and fix line endings
RUN dos2unix start.sh && chmod +x start.sh

# Create directory for Nginx PID file and Cache
RUN mkdir -p /var/run /var/cache/nginx/auth_cache && \
    chmod 755 /var/run && \
    chown -R www-data:www-data /var/cache/nginx

# CRITICAL: Coolify MUST route to port 80 (Nginx), NOT 8501 (Streamlit)
# Port 80 serves: Dashboard at / and Streamlit at /lab via proxy
EXPOSE 80

# Health check (check Nginx)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/ || exit 1

# Run the start script
CMD ["./start.sh"]

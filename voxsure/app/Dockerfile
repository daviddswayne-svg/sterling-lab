# Use a lightweight Python base image
FROM python:3.10-slim

# Set the working directory
WORKDIR /usr/share/nginx/html

# Copy the frontend files
COPY . .

# Expose port 8033
EXPOSE 8033

# Use Python's built-in HTTP server for simplicity
CMD ["python", "-m", "http.server", "8033"]

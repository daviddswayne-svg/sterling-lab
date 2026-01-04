# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Install system dependencies for 3D processing (trimesh/rtree)
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the backend code into the container
COPY . .

# Install Python packages
RUN pip install --no-cache-dir fastapi uvicorn trimesh numpy Pillow python-multipart rtree

# Expose the port FastAPI runs on
EXPOSE 8088

# Run the backend
CMD ["python", "main.py"]

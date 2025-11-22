# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for faiss-cpu
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    g++ \
    libopenblas-dev \
    && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory inside the container to /app
WORKDIR /app

# Copy the requirements file first to leverage Docker layer caching
COPY requirements.txt .

# Install Python dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the *entire* project directory contents into the container's /app directory
COPY . .

# (Optional) Create the directory for FAISS index persistence
RUN mkdir -p ./faiss_index

# (Optional) Create the directory for model caching
RUN mkdir -p ./models_cache

# Expose the port the app runs on (Render will use the PORT env var, but this is good practice)
# Do NOT hardcode 8000 here if relying on env var for uvicorn
EXPOSE 8000 10000 

# Command to run the application using uvicorn
# Use exec form and read the PORT environment variable
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
# This uses ${PORT:-8000}, which means use $PORT if set, otherwise default to 8000
# Render will set $PORT, so it should use the correct port.
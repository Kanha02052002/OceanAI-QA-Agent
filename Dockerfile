# Use an official Python runtime as the base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application using uvicorn
# Use exec form to avoid shell interpretation issues
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
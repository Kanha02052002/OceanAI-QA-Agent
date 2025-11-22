FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy the requirements.txt file first to leverage Docker layer caching
# It should be in the same directory as the Dockerfile (i.e., ui/)
COPY requirements.txt .

# Install Python dependencies using pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Streamlit app file (ui.py) from the current directory (ui/) to the app directory in the container
# If your Streamlit file is named differently, adjust the source name here.
COPY ui.py ./ui.py

# Expose the port Streamlit runs on
EXPOSE 8501

# Command to run the application using streamlit
# Ensure the command points to the file copied in the previous step
CMD ["streamlit", "run", "ui.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
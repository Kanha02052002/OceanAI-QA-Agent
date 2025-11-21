FROM python:3.10-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install --no-cache-dir uv
# COPY uv.lock pyproject.toml 
# RUN uv pip install --system --no-cache-dir -r uv.lock 

COPY app/ ./app/
RUN mkdir -p ./faiss_index
RUN mkdir -p ./models_cache
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"] 
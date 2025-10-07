# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY ../requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app/analytics_backend
WORKDIR /app/analytics_backend
EXPOSE 8001
CMD ["uvicorn", "server_utils.analytics_backend.main:app", "--host", "0.0.0.0", "--port", "8001"]

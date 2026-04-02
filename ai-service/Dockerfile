FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ai-service/requirements.txt /app/ai-service/requirements.txt
RUN python -m pip install --no-cache-dir -r /app/ai-service/requirements.txt

COPY ai-service /app/ai-service
WORKDIR /app/ai-service

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN pip install --no-cache-dir fastapi uvicorn sqlalchemy psycopg2-binary langgraph langchain langchain-openai python-dotenv

EXPOSE 8000

CMD ["python", "main.py"]


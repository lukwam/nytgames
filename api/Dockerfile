FROM python:3.12-slim

WORKDIR /app

COPY api/requirements.txt api/requirements.txt
RUN pip install -r api/requirements.txt

COPY pyproject.toml README.md LICENSE ./
COPY nytgames nytgames
RUN pip install --no-deps .

COPY api api
WORKDIR /app/api

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

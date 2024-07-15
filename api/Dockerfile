FROM python:3.12-slim

COPY requirements.txt requirements.txt

RUN pip install -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

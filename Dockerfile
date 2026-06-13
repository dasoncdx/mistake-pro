FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt -q

COPY . .

EXPOSE 8080
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}

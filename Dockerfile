FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app
COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000
CMD ["sh", "-c", "uvicorn izfin_api.main:app --host 0.0.0.0 --port ${PORT}"]

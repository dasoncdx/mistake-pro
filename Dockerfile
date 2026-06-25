FROM python:3.12-slim

# 系统依赖（OpenCV + weasyprint + 中文字体）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    libpango-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 libffi8 shared-mime-info \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["uvicorn", "run:app", "--host", "0.0.0.0", "--port", "8080"]

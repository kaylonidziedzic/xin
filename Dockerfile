FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

# 安装系统依赖与 Chromium
RUN apt-get update && apt-get install -y \
    wget gnupg ca-certificates xvfb \
    fonts-liberation fonts-wqy-zenhei \
    libxss1 chromium \
    --no-install-recommends && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

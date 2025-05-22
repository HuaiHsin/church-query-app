# 基礎映像：Python + Tesseract 安裝版
FROM python:3.11-slim

# 安裝 Tesseract 與繁體中文語言包 +其他依賴
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-chi-tra \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && apt-get clean

# 設定工作目錄
WORKDIR /app

# 複製所有檔案進容器
COPY . /app

# 安裝 Python 套件
RUN pip install --no-cache-dir -r requirements.txt

# 啟動 FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]

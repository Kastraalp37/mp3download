# Python 3.11 slim tabanlı küçük bir imaj kullan
FROM python:3.11-slim

# Çalışma dizini
WORKDIR /app

# Gerekli sistem paketlerini yükle (yt-dlp için ffmpeg gerekir)
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Gereksinimleri yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# 8000 portunu aç
EXPOSE 8000

# Uygulamayı başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"] 
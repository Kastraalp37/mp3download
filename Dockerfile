# Python 3.9 base image kullan
FROM python:3.9-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Gerekli sistem paketlerini yükle
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Gerekli Python paketlerini kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# İndirme dizinini oluştur
RUN mkdir -p downloads

# Port ayarı
EXPOSE 5000

# Uygulamayı çalıştır
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"] 
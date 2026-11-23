FROM python:3.11-slim

WORKDIR /app

# Gerekli bağımlılıkları kopyala ve yükle
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama kodlarını kopyala
COPY . .

# Uploads ve veritabanı dizinlerinin izinlerini hazırla
RUN mkdir -p uploads

# Port tanımlaması
EXPOSE 5000

ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Başlatma komutu
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:app"]

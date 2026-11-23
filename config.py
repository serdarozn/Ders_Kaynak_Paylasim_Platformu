import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# .env dosyası varsa ortam değişkenlerini otomatik yükle
env_path = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))

raw_db_url = os.environ.get(
    'DATABASE_URL',
    'sqlite:///' + os.path.join(BASE_DIR, 'database.db')
)
# Render / Heroku postgres:// URI formatını SQLAlchemy 2.x uyumlu postgresql:// formatına dönüştür
if raw_db_url.startswith('postgres://'):
    raw_db_url = raw_db_url.replace('postgres://', 'postgresql://', 1)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'selcuk-ceng-topluma-hizmet-gizli-anahtar-2026')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Dosya Yükleme Ayarları
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 Megabyte sınırı
    ALLOWED_EXTENSIONS = {'pdf', 'jpg', 'jpeg', 'png'}

from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def get_utc_now():
    return datetime.now(timezone.utc)

class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), default='Bilgisayar Mühendisliği', nullable=False, index=True) # Bölüm
    course_code = db.Column(db.String(20), nullable=False, index=True)
    course_name = db.Column(db.String(150), nullable=False)
    class_level = db.Column(db.Integer, nullable=False, index=True)  # 1, 2, 3 veya 4
    exam_type = db.Column(db.String(20), nullable=False, index=True)   # Vize, Final, Genel
    file_path = db.Column(db.String(300), nullable=False)             # uploads içindeki dosya adı
    file_type = db.Column(db.String(10), nullable=False)              # pdf, jpg, png
    file_size = db.Column(db.Integer, default=0)                      # Bayt cinsinden boyut
    description = db.Column(db.Text, nullable=True)                   # İsteğe bağlı ek açıklama
    download_count = db.Column(db.Integer, default=0)
    upvotes = db.Column(db.Integer, default=0)
    downvotes = db.Column(db.Integer, default=0)
    report_count = db.Column(db.Integer, default=0)
    last_report_reason = db.Column(db.String(300), nullable=True, default='')
    is_approved = db.Column(db.Boolean, default=False, nullable=False, index=True) # Yönetici onayı
    created_at = db.Column(db.DateTime, default=get_utc_now)

    def __init__(
        self, title, course_code, course_name, class_level, exam_type,
        file_path, file_type, file_size=0, description=None,
        download_count=0, upvotes=0, downvotes=0, report_count=0,
        is_approved=False, department='Bilgisayar Mühendisliği', created_at=None,
        last_report_reason=''
    ):
        self.title = title
        self.department = department
        self.course_code = course_code
        self.course_name = course_name
        self.class_level = class_level
        self.exam_type = exam_type
        self.file_path = file_path
        self.file_type = file_type
        self.file_size = file_size
        self.description = description
        self.download_count = download_count
        self.upvotes = upvotes
        self.downvotes = downvotes
        self.report_count = report_count
        self.last_report_reason = last_report_reason
        self.is_approved = is_approved
        if created_at is not None:
            self.created_at = created_at

    @property
    def score(self):
        """Net beğeni skoru (Faydalı - Yetersiz)"""
        return self.upvotes - self.downvotes

    @property
    def formatted_size(self):
        """İnsan tarafından okunabilir dosya boyutu (KB / MB)"""
        if not self.file_size or self.file_size == 0:
            return "Bilinmiyor"
        size = float(self.file_size)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    @property
    def formatted_date(self):
        """Türkçe formatında tarih çıktısı"""
        if not self.created_at:
            return ""
        months = [
            "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
            "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"
        ]
        month_name = months[self.created_at.month - 1]
        return f"{self.created_at.day} {month_name} {self.created_at.year}"

    @property
    def badge_class_for_level(self):
        badges = {
            1: "badge-lvl-1",
            2: "badge-lvl-2",
            3: "badge-lvl-3",
            4: "badge-lvl-4"
        }
        return badges.get(self.class_level, "badge-secondary")

    @property
    def badge_class_for_exam(self):
        badges = {
            "Vize": "badge-exam-vize",
            "Final": "badge-exam-final",
            "Genel": "badge-exam-genel"
        }
        return badges.get(self.exam_type, "badge-secondary")

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'department': self.department,
            'course_code': self.course_code,
            'course_name': self.course_name,
            'class_level': self.class_level,
            'exam_type': self.exam_type,
            'file_type': self.file_type,
            'file_size': self.formatted_size,
            'download_count': self.download_count,
            'upvotes': self.upvotes,
            'downvotes': self.downvotes,
            'score': self.score,
            'report_count': self.report_count,
            'last_report_reason': self.last_report_reason or "",
            'is_approved': self.is_approved,
            'created_at': self.formatted_date,
            'description': self.description or ""
        }

    def __repr__(self):
        return f"<Note {self.id}: {self.course_code} - {self.title}>"

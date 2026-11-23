"""
Veritabanı Kurulum ve Güncelleme Betiği (init_db.py)
Kullanım:
    python init_db.py          -> Eksik tabloları ve 'is_approved' sütununu ekler/günceller.
    python init_db.py --reset  -> Veritabanını tamamen sıfırlar ve şemayı baştan oluşturur.
"""

import sys
import os
import sqlite3
from app import app, db, restore_notes_from_backup, save_notes_backup
from models import Note

def migrate_sqlite():
    """Mevcut SQLite veritabanında is_approved kolonu yoksa ekler."""
    db_path = os.path.join(os.path.dirname(__file__), 'database.db')
    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(notes)")
    columns = [col[1] for col in cur.fetchall()]

    if 'notes' in [row[0] for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        if 'is_approved' not in columns:
            print("[MİGRASYON] 'is_approved' kolonu tespit edilemedi, ekleniyor...")
            cur.execute("ALTER TABLE notes ADD COLUMN is_approved BOOLEAN DEFAULT 1 NOT NULL")
            conn.commit()
            print("[MİGRASYON] 'is_approved' kolonu başarıyla eklendi (mevcut kayıtlar onaylandı).")

        if 'department' not in columns:
            print("[MİGRASYON] 'department' kolonu tespit edilemedi, ekleniyor...")
            cur.execute("ALTER TABLE notes ADD COLUMN department VARCHAR(100) DEFAULT 'Bilgisayar Mühendisliği' NOT NULL")
            conn.commit()
            print("[MİGRASYON] 'department' kolonu başarıyla eklendi.")

        if 'last_report_reason' not in columns:
            print("[MİGRASYON] 'last_report_reason' kolonu tespit edilemedi, ekleniyor...")
            cur.execute("ALTER TABLE notes ADD COLUMN last_report_reason VARCHAR(300) DEFAULT ''")
            conn.commit()
            print("[MİGRASYON] 'last_report_reason' kolonu başarıyla eklendi.")

    conn.close()

def init_database(reset=False):
    with app.app_context():
        if reset:
            print("[UYARI] Veritabanı sıfırlanıyor (Drop all)...")
            db.drop_all()
            print("[BİLGİ] Tablolar yeniden oluşturuluyor...")
            db.create_all()
            print("[BAŞARILI] Veritabanı şeması tertemiz kuruldu.")
        else:
            migrate_sqlite()
            print("[BİLGİ] Veritabanı tabloları doğrulanıyor...")
            db.create_all()
            restore_notes_from_backup()
            save_notes_backup()
            print("[BAŞARILI] Veritabanı hazır ve güncel.")

        # Mevcut kayıt sayısını kontrol et
        count = Note.query.count()
        print(f"[DURUM] Veritabanında toplam {count} adet not bulunmaktadır.")

if __name__ == '__main__':
    reset_flag = '--reset' in sys.argv
    init_database(reset=reset_flag)

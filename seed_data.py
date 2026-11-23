import os
import random
from datetime import datetime, timedelta, timezone

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

from app import app, db
from models import Note

# Renk paleti
COLORS = [
    ("#0f766e", "#14b8a6"), # Teal / Turkuaz (Selçuk Üniversitesi tonları)
    ("#1e3a8a", "#3b82f6"), # Royal Blue
    ("#4338ca", "#6366f1"), # Indigo
    ("#065f46", "#10b981"), # Emerald
    ("#831843", "#ec4899"), # Rose
    ("#7c2d12", "#f97316"), # Amber / Orange
]

SAMPLE_NOTES = [
    # --- BİLGİSAYAR MÜHENDİSLİĞİ ---
    {
        "department": "Bilgisayar Mühendisliği",
        "course_code": "3301156",
        "course_name": "BİLGİSAYAR MÜHENDİSLİĞİNE GİRİŞ",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Bilgisayar Mühendisliği Temelleri, Sayı Sistemleri ve Donanım Özeti",
        "description": "İkili (Binary), Sekizli ve Onaltılı sayı dönüşümleri, mantıksal mimari ve temel programlama kavramları vize hazırlık notu.",
        "file_type": "pdf",
        "download_count": 142,
        "upvotes": 38,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "department": "Bilgisayar Mühendisliği",
        "course_code": "3301256",
        "course_name": "PROGRAMLAMA DİLİ-1",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "C/C++ Temel Sözdizimi, Diziler, Göstericiler (Pointers) ve Fonksiyonlar",
        "description": "Bellek tahsisi (malloc/free), dinamik diziler, işaretçi aritmetiği ve örnek sınav kodları.",
        "file_type": "pdf",
        "download_count": 128,
        "upvotes": 35,
        "downvotes": 0,
        "report_count": 0
    },
    {
        "department": "Bilgisayar Mühendisliği",
        "course_code": "3301354",
        "course_name": "VERİ YAPILARI VE UYGULAMALARI",
        "class_level": 2,
        "exam_type": "Final",
        "title": "Bağlı Listeler, İkili Arama Ağaçları (BST) ve AVL Ağaçları",
        "description": "Yığın (Stack), kuyruk (Queue), bağlı liste implementasyonları ve ağaç rotasyon adımları görselleştirmeli ders notu.",
        "file_type": "pdf",
        "download_count": 310,
        "upvotes": 84,
        "downvotes": 3,
        "report_count": 0
    },
    {
        "department": "Bilgisayar Mühendisliği",
        "course_code": "3301454",
        "course_name": "VERİTABANI YÖNETİM SİSTEMLERİ",
        "class_level": 2,
        "exam_type": "Final",
        "title": "İlişkisel Cebir, Normalizasyon (1NF, 2NF, 3NF, BCNF) ve SQL Sorguları",
        "description": "E-R diyagramları dönüştürme, karmaşık SQL sorguları, indeksleme ve transaction ACID prensipleri.",
        "file_type": "pdf",
        "download_count": 340,
        "upvotes": 96,
        "downvotes": 4,
        "report_count": 1
    },
    {
        "department": "Bilgisayar Mühendisliği",
        "course_code": "3301651",
        "course_name": "YAPAY ZEKA",
        "class_level": 3,
        "exam_type": "Final",
        "title": "Arama Algoritmaları (A*, BFS, DFS), Minimax ve Makine Öğrenmesi",
        "description": "Sezgisel arama stratejileri, oyun ağaçları, alfa-beta budama ve temel yapay sinir ağı kavramları.",
        "file_type": "pdf",
        "download_count": 265,
        "upvotes": 71,
        "downvotes": 2,
        "report_count": 0
    },

    # --- ELEKTRİK-ELEKTRONİK MÜHENDİSLİĞİ ---
    {
        "department": "Elektrik-Elektronik Mühendisliği",
        "course_code": "3302157",
        "course_name": "ELEKTRİK-ELEKTRONİK MÜH. GİRİŞ",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Temel Elektrik Kavramları, Akım, Gerilim ve Güç Bağıntıları",
        "description": "Ohm Yasası, Kirchhoff Akım ve Gerilim Yasaları, temel devre elemanları ve ölçüm aletleri özeti.",
        "file_type": "pdf",
        "download_count": 115,
        "upvotes": 31,
        "downvotes": 0,
        "report_count": 0
    },
    {
        "department": "Elektrik-Elektronik Mühendisliği",
        "course_code": "3302352",
        "course_name": "DEVRE ANALİZİ-1",
        "class_level": 2,
        "exam_type": "Vize",
        "title": "Düğüm Gerilimleri, Çevre Akımları, Thevenin ve Norton Teoremleri",
        "description": "Devre analizi yöntemleri, süperpozisyon teoremi, bağımlı kaynaklı devreler ve çözümlü vize soruları.",
        "file_type": "pdf",
        "download_count": 240,
        "upvotes": 68,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "department": "Elektrik-Elektronik Mühendisliği",
        "course_code": "3302353",
        "course_name": "ELEKTRONİK-1",
        "class_level": 2,
        "exam_type": "Final",
        "title": "Diyot Karakteristiği, Zener Diyotlar, BJT ve MOSFET Kutuplama",
        "description": "Yarı iletken fiziği, doğrultucu devreler, BJT transistör çalışma bölgeleri ve küçük sinyal eşdeğer modelleri.",
        "file_type": "jpg",
        "download_count": 195,
        "upvotes": 52,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "department": "Elektrik-Elektronik Mühendisliği",
        "course_code": "3302355",
        "course_name": "ELEKTROMANYETİK ALAN TEORİSİ",
        "class_level": 2,
        "exam_type": "Vize",
        "title": "Vektör Analizi, Coulomb ve Gauss Yasaları, Elektrostatik Potansiyel",
        "description": "Kartezyen, silindirik ve küresel koordinat sistemleri, diverjans, gradyen, curl işlemleri ve Laplace denklemi.",
        "file_type": "pdf",
        "download_count": 160,
        "upvotes": 44,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "department": "Elektrik-Elektronik Mühendisliği",
        "course_code": "3302553",
        "course_name": "GÜÇ ELEKTRONİĞİ",
        "class_level": 3,
        "exam_type": "Final",
        "title": "Tristörler, Kontrollü Doğrultucular, DC-DC Kıyıcılar (Buck/Boost)",
        "description": "Anahtarlama kayıpları, PWM tekniği, inverter topolojileri ve endüstriyel güç devreleri formül kartı.",
        "file_type": "png",
        "download_count": 180,
        "upvotes": 49,
        "downvotes": 1,
        "report_count": 0
    },

    # --- MAKİNE MÜHENDİSLİĞİ ---
    {
        "department": "Makine Mühendisliği",
        "course_code": "3303115",
        "course_name": "MAKİNE MÜHENDİSLİĞİNE GİRİŞ",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Mühendislik Birimleri, Kuvvet Sistemleri ve Temel İmalat Yöntemleri",
        "description": "SI birim sistemi dönüşümleri, mesleki etik, talaşlı ve talaşsız imalat süreçleri genel bakış.",
        "file_type": "pdf",
        "download_count": 105,
        "upvotes": 29,
        "downvotes": 0,
        "report_count": 0
    },
    {
        "department": "Makine Mühendisliği",
        "course_code": "3303121",
        "course_name": "TEKNİK RESİM-1",
        "class_level": 1,
        "exam_type": "Vize",
        "title": "Görünüş Çıkarma, Ölçülendirme Kuralları ve Kesit Alma Yöntemleri",
        "description": "İzometrik ve eğik izdüşüm, standart çizgiler, geometrik toleranslar ve teknik çizim kuralları rehberi.",
        "file_type": "pdf",
        "download_count": 225,
        "upvotes": 63,
        "downvotes": 1,
        "report_count": 0
    },
    {
        "department": "Makine Mühendisliği",
        "course_code": "3303305",
        "course_name": "STATİK",
        "class_level": 2,
        "exam_type": "Vize",
        "title": "Maddi Noktaların Dengesi, Rijit Cisimler, Kafes Sistemler ve Sürtünme",
        "description": "Serbest cisim diyagramı (SCD), mesnet tepkileri, ağırlık merkezi ve düğüm noktaları analiz yöntemleri.",
        "file_type": "pdf",
        "download_count": 280,
        "upvotes": 79,
        "downvotes": 2,
        "report_count": 0
    },
    {
        "department": "Makine Mühendisliği",
        "course_code": "3303302",
        "course_name": "TERMODİNAMİK-1",
        "class_level": 2,
        "exam_type": "Final",
        "title": "Termodinamiğin 1. ve 2. Yasaları, Kapalı ve Açık Sistem Analizleri",
        "description": "Saf maddelerin özellikleri, buhar tabloları kullanımı, entropi değişimi ve Carnot çevrimi problem çözümleri.",
        "file_type": "png",
        "download_count": 315,
        "upvotes": 88,
        "downvotes": 3,
        "report_count": 0
    },
    {
        "department": "Makine Mühendisliği",
        "course_code": "3303502",
        "course_name": "AKIŞKANLAR MEKANİĞİ",
        "class_level": 3,
        "exam_type": "Final",
        "title": "Akışkan Statiği, Bernoulli Denklemi ve Borularda Sürtünme Kayıpları",
        "description": "Manometre hesaplamaları, kontrol hacmi kütle/momentum korunumu, Moody diyagramı ve laminer/türbülanslı akış.",
        "file_type": "pdf",
        "download_count": 250,
        "upvotes": 72,
        "downvotes": 1,
        "report_count": 0
    }
]


def create_sample_document(file_path, file_type, course_code, course_name, title, exam_type):
    """Pillow kütüphanesi varsa şık önizleme dosyası, yoksa standart minimal dosya oluşturur."""
    if not HAS_PIL:
        if file_type.lower() == 'pdf':
            pdf_data = (
                b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
                b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
                b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n"
                b"4 0 obj\n<< /Length 55 >>\nstream\nBT /F1 18 Tf 50 700 Td (Selcuk Uni Bilgisayar Muh - Ders Notu) Tj ET\nendstream\nendobj\n"
                b"xref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000206 00000 n \n"
                b"trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n310\n%%EOF\n"
            )
            with open(file_path, 'wb') as f:
                f.write(pdf_data)
        else:
            # 1x1 piksel şeffaf PNG binary
            png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
            with open(file_path, 'wb') as f:
                f.write(png_data)
        return

    width, height = 1200, 1600
    color_bg = (248, 250, 252)  # slate-50
    header_color = (15, 118, 110)  # Selçuk turquoise (#0f766e)

    img = Image.new('RGB', (width, height), color=color_bg)
    draw = ImageDraw.Draw(img)

    # Üst banner
    draw.rectangle([(0, 0), (width, 220)], fill=header_color)

    # Başlık ve Üst Bilgi
    draw.text((60, 40), "SELÇUK ÜNİVERSİTESİ BİLGİSAYAR MÜHENDİSLİĞİ", fill=(255, 255, 255))
    draw.text((60, 80), "Topluma Hizmet Uygulamaları - Açık Ders Notu Havuzu", fill=(204, 251, 241))
    draw.text((60, 140), f"{course_code} - {course_name} ({exam_type} Notu)", fill=(255, 255, 255))

    # Not Gövdesi Kartı
    draw.rectangle([(60, 270), (width - 60, height - 120)], fill=(255, 255, 255), outline=(226, 232, 240), width=3)

    # Başlık
    draw.text((100, 320), f"Konu: {title}", fill=(15, 23, 42))

    # İçerik maddeleri
    lines = [
        "1. TEMEL KAVRAMLAR VE TANIMLAR",
        "   - Bu ders notu Selçuk Üniversitesi öğrencileri arasındaki akademik dayanışmayı",
        "     güçlendirmek amacıyla hazırlanmış açık kaynak bir kaynak özetidir.",
        "   - Ders içeriğindeki temel teoremler, sözdizimi kuralları ve algoritmalar derlenmiştir.",
        "",
        "2. ÖNEMLİ FORMÜLLER VE İPUÇLARI",
        "   - Sınav hazırlığında dikkat edilmesi gereken anahtar yöntemler ve zaman karmaşıklıkları.",
        "   - Soru çözüm adımlarında pratik kısayollar ve kontrol basamakları.",
        "",
        "3. UYGULAMA VE ÖRNEK PROBLEM ÇÖZÜMLERİ",
        "   - Adım adım algoritma yürütme (Trace table) ve bellek yönetimi analizleri.",
        "   - Vize ve Final sorularında sıkça karşılaşılan senaryolar.",
        "",
        "----------------------------------------------------------------------------------",
        "Dayanışma Paylaştıkça Büyür! Başarılar dileriz.",
        "Selçuk Üniversitesi Bilgisayar Mühendisliği Bölümü Öğrenci İnisiyatifi"
    ]

    y_offset = 400
    for line in lines:
        draw.text((100, y_offset), line, fill=(51, 65, 85))
        y_offset += 45

    # Alt Bilgi Çubuğu
    draw.rectangle([(0, height - 70), (width, height)], fill=(15, 23, 42))
    draw.text((60, height - 45), "Ders Notu ve Kaynak Dayanışma Platformu • Lisans: Açık Not Havuzu (CC-BY)", fill=(148, 163, 184))

    if file_type.lower() == 'pdf':
        img.save(file_path, "PDF", resolution=100.0)
    elif file_type.lower() in ['jpg', 'jpeg']:
        img.save(file_path, "JPEG", quality=90)
    else:
        img.save(file_path, "PNG")


def seed():
    with app.app_context():
        # Tabloları oluştur
        db.create_all()

        # Eğer zaten notlar varsa tekrar ekleme
        existing_count = Note.query.count()
        if existing_count > 0:
            print(f"Veritabanında zaten {existing_count} adet not mevcut. Seed işlemi atlandı.")
            return

        print("Örnek ders notları ve dosyaları oluşturuluyor...")
        base_date = datetime.now(timezone.utc) - timedelta(days=20)

        for i, item in enumerate(SAMPLE_NOTES):
            filename = f"sample_{item['course_code'].lower()}_{item['exam_type'].lower()}_{i+1}.{item['file_type']}"
            file_full_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            # Dosyayı diske oluştur
            create_sample_document(
                file_full_path, 
                item['file_type'],
                item['course_code'], 
                item['course_name'], 
                item['title'],
                item['exam_type']
            )

            file_size = os.path.getsize(file_full_path)

            note = Note(
                title=item['title'],
                department=item.get('department', 'Bilgisayar Mühendisliği'),
                course_code=item['course_code'],
                course_name=item['course_name'],
                class_level=item['class_level'],
                exam_type=item['exam_type'],
                file_path=filename,
                file_type=item['file_type'],
                file_size=file_size,
                description=item['description'],
                download_count=item['download_count'],
                upvotes=item['upvotes'],
                downvotes=item['downvotes'],
                report_count=item['report_count'],
                is_approved=True,  # Örnek notlar doğrudan onaylı yayında başlasın
                created_at=base_date + timedelta(days=i * 2, hours=random.randint(1, 10))
            )
            db.session.add(note)

        db.session.commit()
        print(f"Başarıyla {len(SAMPLE_NOTES)} adet örnek ders notu ve dosyası yüklendi (tümü onaylı)!")


if __name__ == '__main__':
    seed()

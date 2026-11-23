import os
import io
import json
import uuid
import sqlite3
import zipfile
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, 
    jsonify, send_from_directory, send_file, flash, abort, session
)
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
from sqlalchemy import or_, desc, func

from config import Config
from models import db, Note
from bologna_courses import (
    DEPARTMENTS, FACULTY_COURSES, get_courses_by_department, 
    find_course, get_course_name, get_courses_by_class
)

app = Flask(__name__)
app.config.from_object(Config)

# Veritabanını ve yükleme dizinini başlat
db.init_app(app)

# Uploads dizininin var olduğundan emin ol
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

BACKUP_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'notes_backup.json')


def save_notes_backup():
    """Veritabanındaki notları kalıcı JSON yedeğine (notes_backup.json) senkronize eder."""
    if app.config.get('TESTING'):
        return
    try:
        notes = Note.query.order_by(Note.id.asc()).all()
        backup_data = []
        for n in notes:
            backup_data.append({
                'id': n.id,
                'title': n.title,
                'department': n.department,
                'course_code': n.course_code,
                'course_name': n.course_name,
                'class_level': n.class_level,
                'exam_type': n.exam_type,
                'file_path': n.file_path,
                'file_type': n.file_type,
                'file_size': n.file_size,
                'description': n.description or '',
                'download_count': n.download_count,
                'upvotes': n.upvotes,
                'downvotes': n.downvotes,
                'report_count': n.report_count,
                'last_report_reason': n.last_report_reason or '',
                'is_approved': bool(n.is_approved),
                'created_at': n.created_at.isoformat() if n.created_at else None
            })
        with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        app.logger.warning(f"Not yedeği kaydedilirken hata: {e}")


def restore_notes_from_backup():
    """Veritabanı sıfırlanmış veya eksikse notes_backup.json üzerinden notları geri yükler."""
    if app.config.get('TESTING'):
        return
    if not os.path.exists(BACKUP_FILE):
        save_notes_backup()
        return
    try:
        with open(BACKUP_FILE, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        if not isinstance(backup_data, list):
            return

        existing_files = {n.file_path for n in Note.query.all()}
        restored_count = 0

        for item in backup_data:
            file_path = item.get('file_path')
            if not file_path or file_path in existing_files:
                continue

            created_at = None
            raw_dt = item.get('created_at')
            if raw_dt:
                try:
                    created_at = datetime.fromisoformat(raw_dt)
                except ValueError:
                    created_at = datetime.now(timezone.utc)

            note = Note(
                title=item['title'],
                department=item.get('department', 'Bilgisayar Mühendisliği'),
                course_code=item['course_code'],
                course_name=item['course_name'],
                class_level=int(item['class_level']),
                exam_type=item['exam_type'],
                file_path=file_path,
                file_type=item['file_type'],
                file_size=int(item.get('file_size', 0)),
                description=item.get('description', ''),
                download_count=int(item.get('download_count', 0)),
                upvotes=int(item.get('upvotes', 0)),
                downvotes=int(item.get('downvotes', 0)),
                report_count=int(item.get('report_count', 0)),
                last_report_reason=item.get('last_report_reason', ''),
                is_approved=bool(item.get('is_approved', True)),
                created_at=created_at
            )
            db.session.add(note)
            existing_files.add(file_path)
            restored_count += 1

        if restored_count > 0:
            db.session.commit()
            app.logger.info(f"{restored_count} adet not yedekten geri yüklendi.")
        save_notes_backup()
    except Exception as e:
        app.logger.warning(f"Not yedeği geri yüklenirken hata: {e}")


def admin_required(f):
    """Yönetici oturumu gerektiren rotalar için decorator."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Bu sayfaya erişmek için yönetici girişi yapmalısınız.', 'warning')
            return redirect(url_for('admin_login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


@app.context_processor
def inject_admin_status():
    """Tüm şablonlara yönetici oturum durumunu ve bekleyen not sayısını aktarır."""
    is_admin = session.get('is_admin', False)
    pending_notes_count = 0
    if is_admin:
        try:
            pending_notes_count = Note.query.filter_by(is_approved=False).count()
        except Exception:
            pending_notes_count = 0
    return {
        'is_admin': is_admin,
        'pending_notes_count': pending_notes_count
    }


def allowed_file(filename):
    """Dosya uzantısının izin verilen listede olup olmadığını kontrol eder."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def get_file_extension(filename):
    """Dosya uzantısını küçük harfle döndürür."""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


# ==========================================
# SAYFA ROTALARI (PAGE ROUTES)
# ==========================================

@app.route('/')
def index():
    """Ana sayfa: Yalnızca onaylanmış notları listeleme, arama ve filtreleme (Bölüm destekli)."""
    query = Note.query.filter_by(is_approved=True)

    # Filtre parametreleri
    search_q = request.args.get('q', '').strip()
    department = request.args.get('department', '').strip()
    class_level = request.args.get('class_level', '').strip()
    exam_type = request.args.get('exam_type', '').strip()
    file_type = request.args.get('file_type', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    # Bölüm filtresi
    if department:
        if department in DEPARTMENTS.values():
            query = query.filter(Note.department == department)
        elif department in DEPARTMENTS:
            query = query.filter(Note.department == DEPARTMENTS[department])

    # Arama filtresi (Ders Kodu, Ders Adı, Not Başlığı, Bölüm)
    if search_q:
        search_filter = or_(
            Note.title.ilike(f'%{search_q}%'),
            Note.course_code.ilike(f'%{search_q}%'),
            Note.course_name.ilike(f'%{search_q}%'),
            Note.department.ilike(f'%{search_q}%'),
            Note.description.ilike(f'%{search_q}%')
        )
        query = query.filter(search_filter)

    # Sınıf filtresi
    if class_level and class_level.isdigit():
        query = query.filter(Note.class_level == int(class_level))

    # Sınav türü filtresi
    if exam_type and exam_type in ['Vize', 'Final', 'Genel']:
        query = query.filter(Note.exam_type == exam_type)

    # Dosya türü filtresi
    if file_type:
        if file_type.lower() == 'pdf':
            query = query.filter(Note.file_type == 'pdf')
        elif file_type.lower() == 'image':
            query = query.filter(Note.file_type.in_(['jpg', 'jpeg', 'png']))

    # Sıralama
    if sort_by == 'popular':
        query = query.order_by(desc(Note.download_count))
    elif sort_by == 'top_rated':
        query = query.order_by(desc(Note.upvotes - Note.downvotes))
    elif sort_by == 'oldest':
        query = query.order_by(Note.created_at.asc())
    else:  # newest
        query = query.order_by(desc(Note.created_at))

    notes = query.all()

    # Genel İstatistikler (Sadece onaylı notlar)
    total_notes = Note.query.filter_by(is_approved=True).count()
    total_downloads = db.session.query(func.coalesce(func.sum(Note.download_count), 0)).filter(Note.is_approved == True).scalar() or 0
    total_courses = db.session.query(func.count(func.distinct(Note.course_code))).filter(Note.is_approved == True).scalar() or 0
    total_upvotes = db.session.query(func.coalesce(func.sum(Note.upvotes), 0)).filter(Note.is_approved == True).scalar() or 0

    return render_template(
        'index.html',
        notes=notes,
        total_notes=total_notes,
        total_downloads=total_downloads,
        total_courses=total_courses,
        total_upvotes=total_upvotes,
        departments=DEPARTMENTS,
        current_department=department,
        current_search=search_q,
        current_class=class_level,
        current_exam=exam_type,
        current_file_type=file_type,
        current_sort=sort_by
    )


@app.route('/not-yukle')
def upload_page():
    """Not yükleme formu sayfası (Teknoloji Fakültesi tüm bölümleri ile)."""
    return render_template(
        'upload.html', 
        departments=DEPARTMENTS, 
        faculty_courses=FACULTY_COURSES
    )


@app.route('/api/courses', methods=['GET'])
def api_courses():
    """Bologna ders kataloğu API'si (Bölüm ve Sınıf filtreli)."""
    dept = request.args.get('department')
    level = request.args.get('class_level')
    
    courses = get_courses_by_department(dept)
    if level and level.isdigit():
        courses = [c for c in courses if c['class_level'] == int(level)]
        
    return jsonify({
        'success': True,
        'count': len(courses),
        'courses': courses
    })


@app.route('/istatistikler')
def stats_page():
    """Detaylı dayanışma ve platform istatistikleri sayfası (Onaylı notlar)."""
    approved_filter = (Note.is_approved == True)
    total_notes = Note.query.filter(approved_filter).count()
    total_downloads = db.session.query(func.coalesce(func.sum(Note.download_count), 0)).filter(approved_filter).scalar() or 0
    total_upvotes = db.session.query(func.coalesce(func.sum(Note.upvotes), 0)).filter(approved_filter).scalar() or 0
    total_reports = db.session.query(func.coalesce(func.sum(Note.report_count), 0)).scalar() or 0
    total_courses = db.session.query(func.count(func.distinct(Note.course_code))).filter(approved_filter).scalar() or 0

    # Sınıf düzeyine göre dağılım
    class_stats = {1: 0, 2: 0, 3: 0, 4: 0}
    class_counts = db.session.query(Note.class_level, func.count(Note.id)).filter(approved_filter).group_by(Note.class_level).all()
    for level, count in class_counts:
        if level in class_stats:
            class_stats[level] = count

    # Sınav türüne göre dağılım
    exam_stats = {'Vize': 0, 'Final': 0, 'Genel': 0}
    exam_counts = db.session.query(Note.exam_type, func.count(Note.id)).filter(approved_filter).group_by(Note.exam_type).all()
    for etype, count in exam_counts:
        if etype in exam_stats:
            exam_stats[etype] = count

    # Dosya türüne göre dağılım
    file_type_stats = {'pdf': 0, 'görsel': 0}
    ftype_counts = db.session.query(Note.file_type, func.count(Note.id)).filter(approved_filter).group_by(Note.file_type).all()
    for ftype, count in ftype_counts:
        if ftype == 'pdf':
            file_type_stats['pdf'] += count
        else:
            file_type_stats['görsel'] += count

    # En çok indirilen 5 not
    top_downloaded = Note.query.filter(approved_filter).order_by(desc(Note.download_count)).limit(5).all()

    # En yüksek puan alan 5 not (upvotes - downvotes)
    top_rated = Note.query.filter(approved_filter).order_by(desc(Note.upvotes - Note.downvotes)).limit(5).all()

    # En çok not paylaşılan 5 ders
    top_courses = db.session.query(
        Note.course_code, Note.course_name, func.count(Note.id).label('note_count')
    ).filter(approved_filter).group_by(Note.course_code, Note.course_name).order_by(desc('note_count')).limit(5).all()

    return render_template(
        'stats.html',
        total_notes=total_notes,
        total_downloads=total_downloads,
        total_upvotes=total_upvotes,
        total_reports=total_reports,
        total_courses=total_courses,
        class_stats=class_stats,
        exam_stats=exam_stats,
        file_type_stats=file_type_stats,
        top_downloaded=top_downloaded,
        top_rated=top_rated,
        top_courses=top_courses
    )


# ==========================================
# DOSYA İNDİRME VE ÖNİZLEME ROTALARI
# ==========================================

@app.route('/download/<int:id>')
def download_note(id):
    """Dosyayı güvenli bir şekilde indirir ve indirme sayısını 1 artırır."""
    note = db.session.get(Note, id)
    if not note:
        abort(404, description="Not bulunamadı.")

    if not note.is_approved and not session.get('is_admin'):
        abort(404, description="Bu not henüz onaylanmamıştır.")

    full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.file_path)
    if not os.path.exists(full_file_path):
        abort(404, description="Not dosyası sunucuda bulunamadı.")

    # İndirme sayacını artır
    note.download_count += 1
    db.session.commit()
    save_notes_backup()

    # Kullanıcı dostu temiz dosya adı oluştur
    clean_course = secure_filename(note.course_code) or "DERS"
    clean_title = secure_filename(note.title.replace(' ', '_')) or "Not"
    download_filename = f"{clean_course}_{clean_title}.{note.file_type}"

    as_attachment = request.args.get('preview') != '1'

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        note.file_path,
        as_attachment=as_attachment,
        download_name=download_filename
    )


@app.route('/preview/<int:id>')
def preview_note(id):
    """Tarayıcıda önizleme (modal veya yeni sekme) için dosyayı sunar."""
    note = db.session.get(Note, id)
    if not note:
        abort(404, description="Not bulunamadı.")

    if not note.is_approved and not session.get('is_admin'):
        abort(404, description="Bu not henüz onaylanmamıştır.")

    full_file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.file_path)
    if not os.path.exists(full_file_path):
        abort(404, description="Not dosyası sunucuda bulunamadı.")

    return send_from_directory(
        app.config['UPLOAD_FOLDER'],
        note.file_path,
        as_attachment=False
    )


# ==========================================
# REST API ROTALARI
# ==========================================

@app.route('/api/upload', methods=['POST'])
def api_upload():
    """
    Dosya yükleme rotası:
    - secure_filename kontrolü
    - Max 25MB sınırı
    - Sadece .pdf, .jpg, .jpeg, .png formatları
    - SQLite veritabanına kayıt
    """
    # Dosya varlığı kontrolü
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'Lütfen bir dosya seçiniz.'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'message': 'Seçilen dosya adı geçersiz veya boş.'}), 400

    # Form alanlarını al ve doğrula
    title = request.form.get('title', '').strip()
    department = request.form.get('department', '').strip()
    course_name = request.form.get('course_name', '').strip()
    course_code = request.form.get('course_code', '').strip().upper()
    class_level_raw = request.form.get('class_level', '').strip()
    exam_type = request.form.get('exam_type', '').strip()
    description = request.form.get('description', '').strip()

    # Eğer ders kodu yazılmamışsa veya eksikse, ders adı veya katalogdan otomatik eşleştir
    matched_course = None
    if course_code:
        matched_course = find_course(course_code)
    if not matched_course and course_name:
        matched_course = find_course(course_name)

    if matched_course:
        if not course_code:
            course_code = matched_course['code']
        if not course_name:
            course_name = matched_course['name']
        if not department:
            department = matched_course['department_name']
        if not class_level_raw:
            class_level_raw = str(matched_course['class_level'])

    if not course_code:
        course_code = "GENEL"

    if not department:
        department = "Bilgisayar Mühendisliği"

    # Zorunlu alan kontrolü (Artık ders kodunu ezberleyip yazmak zorunlu DEĞİL!)
    if not title or not course_name or not class_level_raw or not exam_type:
        return jsonify({'success': False, 'message': 'Lütfen zorunlu tüm alanları (Başlık, Ders, Sınıf, Sınav Türü) eksiksiz doldurunuz.'}), 400

    try:
        class_level = int(class_level_raw)
        if class_level not in [1, 2, 3, 4]:
            raise ValueError()
    except ValueError:
        return jsonify({'success': False, 'message': 'Geçerli bir sınıf düzeyi seçiniz (1, 2, 3 veya 4).' }), 400

    if exam_type not in ['Vize', 'Final', 'Genel']:
        return jsonify({'success': False, 'message': 'Geçerli bir sınav türü seçiniz (Vize, Final veya Genel).' }), 400

    # Dosya uzantısı kontrolü
    if not allowed_file(file.filename):
        return jsonify({
            'success': False, 
            'message': 'İzin verilmeyen dosya formatı! Sadece PDF, JPG, JPEG ve PNG formatları desteklenmektedir.'
        }), 400

    # Benzersiz ve güvenli dosya adı üretimi
    ext = get_file_extension(file.filename)
    safe_base = secure_filename(file.filename.rsplit('.', 1)[0]) or 'belge'
    unique_filename = f"{uuid.uuid4().hex[:10]}_{safe_base}.{ext}"
    saved_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

    # Dosyayı diske kaydet
    file.save(saved_path)

    # Dosya boyutunu ölç
    file_size = os.path.getsize(saved_path)

    # Yönetici oturumu açıksa doğrudan onaylı yayınla, değilse onay beklesin
    auto_approve = bool(session.get('is_admin'))

    # Veritabanına kaydet
    note = Note(
        title=title,
        department=department,
        course_code=course_code,
        course_name=course_name,
        class_level=class_level,
        exam_type=exam_type,
        file_path=unique_filename,
        file_type=ext,
        file_size=file_size,
        description=description,
        download_count=0,
        upvotes=0,
        downvotes=0,
        report_count=0,
        is_approved=auto_approve
    )

    db.session.add(note)
    db.session.commit()
    save_notes_backup()

    success_msg = (
        'Yönetici olarak yüklediğiniz ders notu doğrudan onaylanarak yayına alındı!'
        if auto_approve else
        'Ders notunuz başarıyla yüklendi! Yönetici onayından sonra platformda yayınlanacaktır.'
    )

    # Standart tarayıcı form navigasyonu ise (AJAX veya API istemcisi değilse) ana sayfaya yönlendir
    if request.headers.get('Accept') == 'text/html' and request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        flash(success_msg, 'success')
        return redirect(url_for('index'))

    return jsonify({
        'success': True,
        'message': success_msg,
        'note_id': note.id
    }), 201


@app.route('/api/vote/<int:id>', methods=['POST'])
def api_vote(id):
    """
    Faydalı / Yetersiz oyu verme API'si (AJAX/Fetch ile asenkron tetiklenir).
    JSON: { "vote_type": "up" | "down" }
    """
    note = db.session.get(Note, id)
    if not note:
        return jsonify({'success': False, 'message': 'Not bulunamadı.'}), 404

    data = request.get_json(silent=True) or request.form
    vote_type = data.get('vote_type')
    previous_vote = data.get('previous_vote')

    if vote_type == 'up':
        if previous_vote == 'down' and note.downvotes > 0:
            note.downvotes -= 1
        note.upvotes += 1
    elif vote_type == 'down':
        if previous_vote == 'up' and note.upvotes > 0:
            note.upvotes -= 1
        note.downvotes += 1
    else:
        return jsonify({'success': False, 'message': 'Geçersiz oy türü. "up" veya "down" olmalıdır.'}), 400

    db.session.commit()
    save_notes_backup()

    return jsonify({
        'success': True,
        'upvotes': note.upvotes,
        'downvotes': note.downvotes,
        'score': note.score,
        'message': 'Oyunuz başarıyla kaydedildi!'
    })


@app.route('/api/report/<int:id>', methods=['POST'])
def api_report(id):
    """
    Hatalı içerik bildirimi API'si.
    JSON: { "reason": "İçerik okunamıyor / Telif / Yanlış ders" }
    """
    note = db.session.get(Note, id)
    if not note:
        return jsonify({'success': False, 'message': 'Not bulunamadı.'}), 404

    data = request.get_json(silent=True) or request.form
    reason = (data.get('reason') or 'Belirtilmedi').strip()

    note.report_count += 1
    note.last_report_reason = reason[:300]
    db.session.commit()
    save_notes_backup()

    return jsonify({
        'success': True,
        'report_count': note.report_count,
        'message': 'Geri bildiriminiz incelenmek üzere kaydedildi. Dayanışma kalitesini koruduğunuz için teşekkür ederiz!'
    })


@app.route('/api/notes', methods=['GET'])
def api_notes():
    """Anlık arama ve filtreleme için onaylı notların JSON listesini döndürür."""
    query = Note.query.filter_by(is_approved=True)

    search_q = request.args.get('q', '').strip()
    class_level = request.args.get('class_level', '').strip()
    exam_type = request.args.get('exam_type', '').strip()
    file_type = request.args.get('file_type', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    if search_q:
        search_filter = or_(
            Note.title.ilike(f'%{search_q}%'),
            Note.course_code.ilike(f'%{search_q}%'),
            Note.course_name.ilike(f'%{search_q}%')
        )
        query = query.filter(search_filter)

    if class_level and class_level.isdigit():
        query = query.filter(Note.class_level == int(class_level))

    if exam_type and exam_type in ['Vize', 'Final', 'Genel']:
        query = query.filter(Note.exam_type == exam_type)

    if file_type:
        if file_type.lower() == 'pdf':
            query = query.filter(Note.file_type == 'pdf')
        elif file_type.lower() == 'image':
            query = query.filter(Note.file_type.in_(['jpg', 'jpeg', 'png']))

    if sort_by == 'popular':
        query = query.order_by(desc(Note.download_count))
    elif sort_by == 'top_rated':
        query = query.order_by(desc(Note.upvotes - Note.downvotes))
    elif sort_by == 'oldest':
        query = query.order_by(Note.created_at.asc())
    else:
        query = query.order_by(desc(Note.created_at))

    notes = query.all()
    return jsonify({
        'success': True,
        'count': len(notes),
        'notes': [n.to_dict() for n in notes]
    })


# ==========================================
# YÖNETİCİ (ADMIN) ROTALARI
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Yönetici giriş sayfası ve doğrulama."""
    if session.get('is_admin'):
        return redirect(url_for('admin_dashboard'))

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        admin_pass = app.config.get('ADMIN_PASSWORD', 'admin123')

        if password == admin_pass:
            session['is_admin'] = True
            flash('Yönetici girişi başarılı. Hoş geldiniz!', 'success')
            next_url = request.args.get('next')
            return redirect(next_url or url_for('admin_dashboard'))
        else:
            flash('Geçersiz yönetici şifresi! Lütfen tekrar deneyiniz.', 'danger')

    return render_template('admin_login.html')


@app.route('/admin/logout')
def admin_logout():
    """Yönetici oturumunu sonlandırır."""
    session.pop('is_admin', None)
    flash('Yönetici oturumu güvenle kapatıldı.', 'info')
    return redirect(url_for('index'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    """Yönetici Kontrol Paneli: Onay bekleyen, yayındaki ve şikayet edilen notlar."""
    pending_notes = Note.query.filter_by(is_approved=False).order_by(desc(Note.created_at)).all()
    approved_notes = Note.query.filter_by(is_approved=True).order_by(desc(Note.created_at)).all()
    reported_notes = Note.query.filter(Note.report_count > 0).order_by(desc(Note.report_count)).all()

    return render_template(
        'admin_dashboard.html',
        pending_notes=pending_notes,
        approved_notes=approved_notes,
        reported_notes=reported_notes,
        pending_count=len(pending_notes),
        approved_count=len(approved_notes),
        reported_count=len(reported_notes),
        departments=DEPARTMENTS
    )


@app.route('/admin/notes/<int:id>/edit', methods=['POST'])
@admin_required
def admin_edit_note(id):
    """Notun başlık, bölüm, ders, sınıf, sınav türü ve açıklamasını düzenler."""
    note = db.session.get(Note, id)
    if not note:
        flash('Düzenlenecek not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    title = request.form.get('title', '').strip()
    department = request.form.get('department', '').strip()
    course_code = request.form.get('course_code', '').strip().upper()
    course_name = request.form.get('course_name', '').strip()
    class_level_raw = request.form.get('class_level', '').strip()
    exam_type = request.form.get('exam_type', '').strip()
    description = request.form.get('description', '').strip()

    if title:
        note.title = title
    if department:
        note.department = department
    if course_code:
        note.course_code = course_code
    if course_name:
        note.course_name = course_name
    if class_level_raw and class_level_raw.isdigit() and int(class_level_raw) in [1, 2, 3, 4]:
        note.class_level = int(class_level_raw)
    if exam_type in ['Vize', 'Final', 'Genel']:
        note.exam_type = exam_type
    note.description = description

    db.session.commit()
    save_notes_backup()
    flash(f'"{note.title}" ({note.course_code}) bilgileri başarıyla güncellendi.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/clear-reports', methods=['POST'])
@admin_required
def admin_clear_reports(id):
    """İncelenen notun şikayet sayacını ve bildirim nedenini sıfırlar."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    note.report_count = 0
    note.last_report_reason = ''
    db.session.commit()
    save_notes_backup()
    flash(f'"{note.title}" üzerindeki şikayet bildirimleri incelendi ve temizlendi.', 'info')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/backup/download')
@admin_required
def admin_download_backup():
    """Tüm veritabanı kayıtlarını (notes_backup.json) ve yüklenen dosyaları (.zip) olarak indirir."""
    save_notes_backup()
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if os.path.exists(BACKUP_FILE):
            zf.write(BACKUP_FILE, arcname='notes_backup.json')
        for note in Note.query.all():
            fpath = os.path.join(app.config['UPLOAD_FOLDER'], note.file_path)
            if os.path.exists(fpath):
                zf.write(fpath, arcname=f"uploads/{note.file_path}")
    memory_file.seek(0)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M')
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        download_name=f"ders_notlari_tam_yedek_{timestamp}.zip"
    )


@app.route('/admin/backup/restore', methods=['POST'])
@admin_required
def admin_restore_backup():
    """Yüklenen .zip veya .json yedeğinden notları ve dosyaları geri yükler."""
    if 'backup_file' not in request.files or request.files['backup_file'].filename == '':
        flash('Lütfen geri yüklenecek bir yedek dosyası (.zip veya .json) seçiniz.', 'warning')
        return redirect(url_for('admin_dashboard'))

    bfile = request.files['backup_file']
    fname = bfile.filename.lower()

    try:
        if fname.endswith('.zip'):
            with zipfile.ZipFile(bfile, 'r') as zf:
                for member in zf.namelist():
                    if member == 'notes_backup.json' or member.endswith('/notes_backup.json'):
                        data = zf.read(member)
                        with open(BACKUP_FILE, 'wb') as f:
                            f.write(data)
                    elif 'uploads/' in member and not member.endswith('/'):
                        base_name = secure_filename(os.path.basename(member))
                        if base_name and allowed_file(base_name):
                            target_path = os.path.join(app.config['UPLOAD_FOLDER'], base_name)
                            with open(target_path, 'wb') as f:
                                f.write(zf.read(member))
        elif fname.endswith('.json'):
            raw_bytes = bfile.read()
            parsed = json.loads(raw_bytes.decode('utf-8'))
            if isinstance(parsed, list):
                with open(BACKUP_FILE, 'wb') as f:
                    f.write(raw_bytes)
            else:
                flash('Geçersiz JSON yedek formatı.', 'danger')
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Sadece .zip veya .json uzantılı yedek dosyaları desteklenmektedir.', 'danger')
            return redirect(url_for('admin_dashboard'))

        restore_notes_from_backup()
        flash('Yedek dosyası başarıyla işlendi ve eksik notlar sisteme geri yüklendi!', 'success')
    except Exception as e:
        flash(f'Yedek geri yüklenirken hata oluştu: {e}', 'danger')

    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/approve', methods=['POST'])
@admin_required
def admin_approve_note(id):
    """Notu onaylar ve sitede yayınlar."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    note.is_approved = True
    db.session.commit()
    save_notes_backup()
    flash(f'"{note.title}" ({note.course_code}) onaylandı ve yayına alındı.', 'success')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/unapprove', methods=['POST'])
@admin_required
def admin_unapprove_note(id):
    """Onaylanmış notu yayından çekip tekrar beklemeye alır."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    note.is_approved = False
    db.session.commit()
    save_notes_backup()
    flash(f'"{note.title}" yayından kaldırıldı ve onay bekleyenlere taşındı.', 'warning')
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/notes/<int:id>/reject', methods=['POST'])
@app.route('/admin/notes/<int:id>/delete', methods=['POST'])
@admin_required
def admin_delete_note(id):
    """Notu ve dosyasını sistemden kalıcı olarak siler."""
    note = db.session.get(Note, id)
    if not note:
        flash('Not bulunamadı.', 'danger')
        return redirect(url_for('admin_dashboard'))

    # Fiziksel dosyayı da sil
    try:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.file_path)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        app.logger.warning(f"Dosya silinirken hata: {e}")

    note_title = note.title
    db.session.delete(note)
    db.session.commit()
    save_notes_backup()

    flash(f'"{note_title}" başarıyla sistemden silindi.', 'info')
    return redirect(url_for('admin_dashboard'))


# ==========================================
# HATA YAKALAYICILAR (ERROR HANDLERS)
# ==========================================

@app.errorhandler(RequestEntityTooLarge)
def handle_file_size_error(e):
    if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': False,
            'message': 'Yüklenen dosya çok büyük! Maksimum izin verilen dosya boyutu 25 MB\'dir.'
        }), 413
    flash('Yüklenen dosya çok büyük! Maksimum izin verilen dosya boyutu 25 MB\'dir.', 'danger')
    return redirect(url_for('upload_page'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('base.html', not_found=True), 404


def ensure_sqlite_columns():
    """Mevcut SQLite veritabanında eksik sütunlar varsa otomatik ekler."""
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if not db_uri.startswith('sqlite:///') or ':memory:' in db_uri:
        return
    db_path = db_uri.replace('sqlite:///', '', 1)
    if not os.path.exists(db_path):
        return
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        if 'notes' in tables:
            cols = [c[1] for c in cur.execute("PRAGMA table_info(notes)").fetchall()]
            if 'is_approved' not in cols:
                cur.execute("ALTER TABLE notes ADD COLUMN is_approved BOOLEAN DEFAULT 1 NOT NULL")
            if 'department' not in cols:
                cur.execute("ALTER TABLE notes ADD COLUMN department VARCHAR(100) DEFAULT 'Bilgisayar Mühendisliği' NOT NULL")
            if 'last_report_reason' not in cols:
                cur.execute("ALTER TABLE notes ADD COLUMN last_report_reason VARCHAR(300) DEFAULT ''")
            conn.commit()
        conn.close()
    except Exception as e:
        app.logger.warning(f"SQLite şema kontrolü sırasında uyarı: {e}")


# CLI Komutu veya ilk çalıştırmada tabloları oluştur ve yedekten senkronize et
with app.app_context():
    ensure_sqlite_columns()
    db.create_all()
    restore_notes_from_backup()

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
